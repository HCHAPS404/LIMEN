"""Conversation orchestrator — coordinates domains without owning their logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from limen.clinical.extraction import extract_from_utterance
from limen.clinical.state import ClinicalState
from limen.clinical.uncertainty_analysis import (
    UncertaintyReport,
    analyze_uncertainty,
    apply_uncertainty,
)
from limen.conversation.context import ConversationContext
from limen.conversation.continuity import (
    filter_open_questions,
    update_context_after_assistant,
    update_context_after_patient,
)
from limen.conversation.response import build_assistant_response
from limen.conversation.turn import Turn
from limen.intelligence.contracts import LLMProvider
from limen.knowledge.contracts import EvidenceChunk, EvidenceRetriever
from limen.safety.decision import SafetyDecision
from limen.safety.governor import SafetyGovernor
from limen.telemetry.cost import cost_not_available
from limen.telemetry.timing import StageTimer
from limen.tracing.contracts import SafetyTracePayload


@dataclass
class TurnResult:
    turn: Turn
    clinical_state: ClinicalState
    safety: SafetyDecision
    evidence: list[EvidenceChunk] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    assistant_text: str = ""
    uncertainty: UncertaintyReport | None = None
    turn_id: str = ""
    safety_trace: SafetyTracePayload | None = None
    provider_error: dict[str, Any] | None = None
    response_meta: dict[str, Any] = field(default_factory=dict)
    conversation: ConversationContext | None = None


class ConversationOrchestrator:
    """Coordinates turn handling with safety floor and optional retrieval."""

    def __init__(
        self,
        governor: SafetyGovernor | None = None,
        retrieval: EvidenceRetriever | None = None,
        llm: LLMProvider | None = None,
        *,
        recent_turns: int = 6,
    ) -> None:
        self.governor = governor or SafetyGovernor()
        self.retrieval = retrieval
        self.llm = llm
        self.recent_turns = recent_turns

    async def handle_text_turn(
        self,
        *,
        call_id: str,
        account_id: str,
        user_text: str,
        clinical_state: ClinicalState,
        conversation: ConversationContext | None = None,
    ) -> TurnResult:
        turn_id = uuid4().hex
        timer = StageTimer()
        timer.mark("speech_end")

        ctx = conversation or ConversationContext(call_id=call_id)
        if not ctx.call_id:
            ctx.call_id = call_id
        answered_before = set(ctx.answered_question_ids)
        ctx = update_context_after_patient(
            ctx, user_text=user_text, max_recent_turns=self.recent_turns
        )
        newly_answered = [
            qid for qid in ctx.answered_question_ids if qid not in answered_before
        ]

        with timer.measure("clinical_extraction"):
            state = extract_from_utterance(user_text, clinical_state)

        with timer.measure("uncertainty"):
            report = analyze_uncertainty(state)
            state = apply_uncertainty(state, report)

        open_questions = filter_open_questions(list(state.open_questions), ctx)
        state.open_questions = open_questions

        evidence: list[EvidenceChunk] = []
        rag_queries = 0
        with timer.measure("retrieval"):
            if report.should_retrieve and self.retrieval is not None:
                evidence = self.retrieval.retrieve(
                    account_id=account_id,
                    query=user_text,
                    limit=4,
                )
                rag_queries = 1

        with timer.measure("safety_evaluation"):
            text_floor = self.governor.evaluate_utterance(user_text)
            state_floor = self.governor.evaluate_state(state)
            floor = self.governor.merge(text_floor, state_floor)
            # Generative path never proposes a weaker decision than GREEN.
            proposed = SafetyDecision.green("generative_default")
            decision = self.governor.enforce_floor(proposed, floor)
            downgrade_protected = decision.severity > proposed.severity or (
                decision.escalate and not proposed.escalate
            )
            safety_trace = SafetyTracePayload(
                floor_severity=floor.severity.name,
                proposed_severity=proposed.severity.name,
                final_severity=decision.severity.name,
                escalate=decision.escalate,
                reasons=list(decision.reasons),
                downgrade_protected=downgrade_protected,
                policy_version=decision.policy_version,
            )

        provider_error: dict[str, Any] | None = None
        with timer.measure("response"):
            (
                assistant,
                llm_calls,
                prompt_tokens,
                completion_tokens,
                llm_meta,
            ) = await build_assistant_response(
                user_text=user_text,
                safety=decision,
                evidence=evidence,
                open_questions=open_questions,
                llm=self.llm,
                clinical_state=state,
                uncertainty=report,
                conversation=ctx,
            )
            if llm_meta.get("error"):
                provider_error = {
                    "stage": "response.generation",
                    "error_category": llm_meta.get("error_category", "provider_error"),
                    "safe_message": llm_meta.get(
                        "safe_message", "LLM provider failed; used template fallback"
                    ),
                    "provider": llm_meta.get("provider"),
                    "retry_count": 0,
                }

        ctx = update_context_after_assistant(
            ctx,
            assistant_text=assistant,
            safety=decision,
            open_questions=open_questions,
            evidence_available=bool(evidence),
            interrupted=False,
            max_recent_turns=self.recent_turns,
        )

        timer.mark("turn_end")
        latency = timer.elapsed_ms("speech_end", "turn_end")
        hybrid_obs = getattr(self.retrieval, "last_metrics", None)
        hybrid: dict[str, Any] = hybrid_obs if isinstance(hybrid_obs, dict) and rag_queries else {}
        cost = cost_not_available(notes="pricing_not_configured")
        evidence_candidates = None
        if hybrid:
            dense_c = hybrid.get("dense_candidates")
            lexical_c = hybrid.get("lexical_candidates")
            if dense_c is not None or lexical_c is not None:
                evidence_candidates = int(dense_c or 0) + int(lexical_c or 0)

        metrics: dict[str, Any] = {
            "latency_ms": latency,
            "total_latency_ms": latency,
            "clinical_ms": timer.stage_ms("clinical_extraction"),
            "uncertainty_ms": timer.stage_ms("uncertainty"),
            "retrieval_ms": timer.stage_ms("retrieval"),
            "safety_ms": timer.stage_ms("safety_evaluation"),
            "response_generation_ms": timer.stage_ms("response"),
            "persistence_ms": None,  # filled by CallService after persist
            "dense_ms": hybrid.get("dense_ms"),
            "lexical_ms": hybrid.get("lexical_ms"),
            "fusion_ms": hybrid.get("fusion_ms"),
            "rag_queries": rag_queries,
            "evidence_candidates": evidence_candidates,
            "evidence_selected": len(evidence),
            "final_evidence_count": len(evidence),
            "llm_calls": llm_calls,
            "input_tokens": prompt_tokens if llm_calls else None,
            "output_tokens": completion_tokens if llm_calls else None,
            "estimated_cost_usd": cost.estimated_cost_usd,
            "cost_basis": cost.cost_basis,
            "uncertainty": report.model_dump(mode="json"),
            "llm_provider": llm_meta.get("provider"),
            "llm_model": llm_meta.get("model"),
            "llm_latency_ms": llm_meta.get("latency_ms"),
            "llm_generation_ms": llm_meta.get("generation_ms"),
            "llm_ttft_ms": llm_meta.get("time_to_first_token_ms"),
            "llm_finish_reason": llm_meta.get("finish_reason"),
            "generated_response_validated": llm_meta.get("generated_response_validated"),
            "response_fallback": llm_meta.get("fallback"),
            "fallback_reason": llm_meta.get("fallback_reason"),
            "degraded_llm_mode": llm_meta.get("degraded_mode"),
            "provider_usage": llm_meta.get("provider_usage"),
            "response_source": llm_meta.get("response_source"),
            "novelty_retry": llm_meta.get("novelty_retry"),
            "conversation_debug": ctx.debug_view(),
            "recent_turns_included": len(ctx.recent_turns),
            "newly_answered_questions": newly_answered,
        }
        turn = Turn(session_id=call_id, user_text=user_text, assistant_text=assistant)
        return TurnResult(
            turn=turn,
            clinical_state=state,
            safety=decision,
            evidence=evidence,
            metrics=metrics,
            assistant_text=assistant,
            uncertainty=report,
            turn_id=turn_id,
            safety_trace=safety_trace,
            provider_error=provider_error,
            response_meta=llm_meta,
            conversation=ctx,
        )
