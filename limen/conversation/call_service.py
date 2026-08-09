"""Application service for call lifecycle (domain + persistence)."""

from __future__ import annotations

import builtins
import time
from typing import Any

from limen.clinical.state import ClinicalState
from limen.clinical.summary import build_call_summary
from limen.config.settings import get_settings
from limen.conversation.context import ConversationContext
from limen.conversation.continuity import mark_interrupted
from limen.conversation.orchestrator import ConversationOrchestrator, TurnResult
from limen.intelligence.contracts import LLMProvider
from limen.knowledge.contracts import EvidenceChunk, EvidenceRetriever
from limen.persistence.repositories.calls import SqliteCallRepository
from limen.persistence.repositories.traces import SqliteTraceRepository
from limen.safety.decision import Severity
from limen.safety.governor import SafetyGovernor
from limen.telemetry.aggregates import aggregate_call_metrics, turn_metrics_from_dict
from limen.telemetry.logging import get_telemetry_logger, log_event

_log = get_telemetry_logger("limen.call")


class CallService:
    def __init__(
        self,
        calls: SqliteCallRepository,
        traces: SqliteTraceRepository,
        retrieval: EvidenceRetriever | None = None,
        governor: SafetyGovernor | None = None,
        llm: LLMProvider | None = None,
    ) -> None:
        self._calls = calls
        self._traces = traces
        settings = get_settings()
        self._orchestrator = ConversationOrchestrator(
            governor=governor or SafetyGovernor(),
            retrieval=retrieval,
            llm=llm,
            recent_turns=settings.conversation_recent_turns,
        )

    def create(
        self,
        *,
        account_id: str,
        patient_alias: str = "Paciente",
        procedure: str | None = None,
        postoperative_day: int | None = None,
    ) -> dict[str, Any]:
        created = self._calls.create_call(
            account_id=account_id,
            patient_alias=patient_alias,
            procedure=procedure,
            postoperative_day=postoperative_day,
        )
        self._traces.append(
            call_id=created["call_id"],
            account_id=account_id,
            stage="call.started",
            event_type="call.started",
            label="Call started",
            detail=patient_alias,
        )
        log_event(_log, "call.started", call_id=created["call_id"])
        return created

    def list(self, account_id: str) -> list[dict[str, Any]]:
        return self._calls.list_calls(account_id)

    def get(self, account_id: str, call_id: str) -> dict[str, Any] | None:
        return self._calls.get_call(account_id, call_id)

    async def process_text_turn(
        self,
        *,
        account_id: str,
        call_id: str,
        user_text: str,
    ) -> TurnResult | None:
        row = self._calls.get_call_row(account_id, call_id)
        if row is None:
            return None
        if row["ended_at"]:
            raise ValueError("Call already finished")

        clinical = ClinicalState.model_validate_json(row["clinical_state_json"] or "{}")
        prior = self._load_call_metrics_blob(row)
        conversation = self._load_conversation_context(prior, call_id=call_id)
        result = await self._orchestrator.handle_text_turn(
            call_id=call_id,
            account_id=account_id,
            user_text=user_text,
            clinical_state=clinical,
            conversation=conversation,
        )

        t_persist = time.perf_counter()
        self._calls.append_turn(call_id=call_id, speaker="patient", text=user_text)
        self._calls.append_turn(call_id=call_id, speaker="agent", text=result.assistant_text)
        persistence_ms = (time.perf_counter() - t_persist) * 1000.0
        result.metrics["persistence_ms"] = persistence_ms

        turns = list(prior.get("turns") or [])
        turns.append(result.metrics)
        call_agg = aggregate_call_metrics(
            [turn_metrics_from_dict(t) for t in turns],
            final_risk=result.safety.severity.name,
            escalated=result.safety.escalate or bool(row["escalated"]),
        )
        conversation_json = (
            result.conversation.model_dump(mode="json") if result.conversation else {}
        )
        metrics_blob = {
            **result.metrics,
            "turns": turns,
            "call": call_agg.model_dump(mode="json"),
            "conversation_context": conversation_json,
            "voice_latencies_ms": prior.get("voice_latencies_ms") or [],
            "voice_interruptions": prior.get("voice_interruptions") or 0,
            "stt_errors": prior.get("stt_errors") or 0,
            "tts_errors": prior.get("tts_errors") or 0,
            "patient_cutoff_count": prior.get("patient_cutoff_count") or 0,
            "false_barge_in_count": prior.get("false_barge_in_count") or 0,
            "stale_audio_discard_count": prior.get("stale_audio_discard_count") or 0,
            "last_safety": {
                "severity": result.safety.severity.name,
                "escalate": result.safety.escalate,
                "reasons": list(result.safety.reasons),
                "policy_version": result.safety.policy_version,
            },
        }
        self._calls.update_runtime(
            account_id=account_id,
            call_id=call_id,
            clinical_state=result.clinical_state,
            final_risk=result.safety.severity.name,
            escalated=result.safety.escalate,
            metrics=metrics_blob,
        )

        turn_id = result.turn_id
        self._traces.append(
            call_id=call_id,
            account_id=account_id,
            stage="patient_statement",
            event_type="turn.received",
            turn_id=turn_id,
            label="Patient utterance",
            detail=user_text[:240],
        )
        self._traces.append(
            call_id=call_id,
            account_id=account_id,
            stage="clinical_extraction",
            event_type="clinical.extraction.completed",
            turn_id=turn_id,
            label="Clinical state updated",
            detail=f"{len(result.clinical_state.findings)} findings",
            duration_ms=result.metrics.get("clinical_ms"),
            payload={"finding_count": len(result.clinical_state.findings)},
        )
        uncertainty = result.uncertainty
        if uncertainty is not None:
            self._traces.append(
                call_id=call_id,
                account_id=account_id,
                stage="uncertainty",
                event_type="clinical.uncertainty.completed",
                turn_id=turn_id,
                label="Uncertainty analysis",
                detail=(
                    f"unresolved={len(uncertainty.unresolved)}; "
                    f"unknown={len(uncertainty.unknown)}; "
                    f"conflicting={len(uncertainty.conflicting)}; "
                    f"should_retrieve={uncertainty.should_retrieve}"
                ),
                duration_ms=result.metrics.get("uncertainty_ms"),
            )
        retrieval_metrics: dict[str, Any] = {
            "rag_queries": result.metrics.get("rag_queries", 0),
            "final_evidence_count": len(result.evidence),
            "evidence_selected": len(result.evidence),
            "evidence_candidates": result.metrics.get("evidence_candidates"),
            "selected_chunk_ids": [c.chunk_id for c in result.evidence],
            "selected_document_ids": sorted({c.document_id for c in result.evidence}),
            "dense_ms": result.metrics.get("dense_ms"),
            "lexical_ms": result.metrics.get("lexical_ms"),
            "fusion_ms": result.metrics.get("fusion_ms"),
            "total_ms": result.metrics.get("retrieval_ms"),
        }
        hybrid_obs = getattr(self._orchestrator.retrieval, "last_metrics", None)
        if isinstance(hybrid_obs, dict) and result.metrics.get("rag_queries"):
            for key in (
                "retrieval_query",
                "dense_candidates",
                "lexical_candidates",
                "retrieval_modes",
            ):
                if key in hybrid_obs:
                    retrieval_metrics[key] = hybrid_obs[key]
            modes: set[str] = set()
            for chunk in result.evidence:
                modes.update(chunk.retrieval_modes)
            if modes:
                retrieval_metrics["retrieval_modes"] = sorted(modes)
        self._traces.append(
            call_id=call_id,
            account_id=account_id,
            stage="retrieval",
            event_type="retrieval.evidence.selected",
            turn_id=turn_id,
            label="Evidence retrieval",
            detail=f"{len(result.evidence)} chunks",
            evidence=result.evidence,
            metrics=retrieval_metrics,
            duration_ms=result.metrics.get("retrieval_ms"),
            payload={
                "dense_ms": result.metrics.get("dense_ms"),
                "lexical_ms": result.metrics.get("lexical_ms"),
                "fusion_ms": result.metrics.get("fusion_ms"),
            },
        )
        safety_payload = result.safety_trace.model_dump(mode="json") if result.safety_trace else {}
        self._traces.append(
            call_id=call_id,
            account_id=account_id,
            stage="safety_evaluation",
            event_type="safety.evaluation.completed",
            turn_id=turn_id,
            label="Safety decision",
            risk=result.safety.severity.name,
            escalate=result.safety.escalate,
            reasons=list(result.safety.reasons),
            duration_ms=result.metrics.get("safety_ms"),
            payload=safety_payload,
        )
        response_meta = result.response_meta or {}
        self._traces.append(
            call_id=call_id,
            account_id=account_id,
            stage="conversation",
            event_type="conversation.context.built",
            turn_id=turn_id,
            label="Conversation context",
            payload=result.metrics.get("conversation_debug") or {},
        )
        newly_answered = result.metrics.get("newly_answered_questions") or []
        if newly_answered:
            self._traces.append(
                call_id=call_id,
                account_id=account_id,
                stage="conversation",
                event_type="conversation.question.answered",
                turn_id=turn_id,
                label="Pending question answered",
                payload={"question_ids": newly_answered},
            )
        if result.conversation and result.conversation.pending_question is not None:
            pq = result.conversation.pending_question
            self._traces.append(
                call_id=call_id,
                account_id=account_id,
                stage="conversation",
                event_type="conversation.pending_question",
                turn_id=turn_id,
                label="Pending question set",
                detail=pq.text[:160],
                payload=pq.model_dump(mode="json"),
            )
        if result.conversation and result.conversation.pending_assistant_intent is not None:
            pai = result.conversation.pending_assistant_intent
            self._traces.append(
                call_id=call_id,
                account_id=account_id,
                stage="conversation",
                event_type=(
                    "conversation.intent.pending"
                    if not pai.completed
                    else "conversation.intent.completed"
                ),
                turn_id=turn_id,
                label="Assistant intent",
                payload=pai.model_dump(mode="json"),
            )
        self._traces.append(
            call_id=call_id,
            account_id=account_id,
            stage="response",
            event_type="response.generation.started",
            turn_id=turn_id,
            label="Response generation started",
            payload={
                "provider": response_meta.get("provider") or result.metrics.get("llm_provider"),
                "model": response_meta.get("model") or result.metrics.get("llm_model"),
                "degraded_mode": response_meta.get("degraded_mode"),
            },
        )
        self._traces.append(
            call_id=call_id,
            account_id=account_id,
            stage="response",
            event_type="response.generation.completed",
            turn_id=turn_id,
            label="Agent response",
            detail=result.assistant_text[:240],
            metrics=result.metrics,
            duration_ms=result.metrics.get("response_generation_ms"),
            payload={
                "turn_metrics": result.metrics,
                "generated_response_validated": response_meta.get(
                    "generated_response_validated"
                ),
                "fallback": response_meta.get("fallback"),
                "fallback_reason": response_meta.get("fallback_reason"),
                "response_source": response_meta.get("response_source"),
                "novelty_retry": response_meta.get("novelty_retry"),
                "provider_usage": response_meta.get("provider_usage")
                or result.metrics.get("provider_usage"),
                "conversation_debug": result.metrics.get("conversation_debug"),
            },
        )
        if response_meta.get("fallback"):
            self._traces.append(
                call_id=call_id,
                account_id=account_id,
                stage="response",
                event_type="response.fallback",
                turn_id=turn_id,
                label="Deterministic response fallback",
                detail=str(response_meta.get("fallback_reason") or "fallback"),
                payload={
                    "fallback_reason": response_meta.get("fallback_reason"),
                    "generated_response_validated": response_meta.get(
                        "generated_response_validated"
                    ),
                },
            )
        if result.provider_error:
            self._traces.append(
                call_id=call_id,
                account_id=account_id,
                stage="provider.error",
                event_type="provider.error",
                turn_id=turn_id,
                label="Provider error",
                detail=result.provider_error.get("safe_message"),
                status="error",
                payload=result.provider_error,
            )
        if result.safety.escalate:
            self._traces.append(
                call_id=call_id,
                account_id=account_id,
                stage="escalation",
                event_type="safety.evaluation.completed",
                turn_id=turn_id,
                label="Escalation triggered",
                risk=result.safety.severity.name,
                escalate=True,
                reasons=list(result.safety.reasons),
            )
        log_event(
            _log,
            "turn.completed",
            call_id=call_id,
            turn_id=turn_id,
            duration_ms=result.metrics.get("latency_ms"),
            rag_queries=result.metrics.get("rag_queries"),
            llm_calls=result.metrics.get("llm_calls"),
        )
        return result

    def finish(self, *, account_id: str, call_id: str) -> dict[str, Any] | None:
        row = self._calls.get_call_row(account_id, call_id)
        if row is None:
            return None
        clinical = ClinicalState.model_validate_json(row["clinical_state_json"] or "{}")
        risk = row["final_risk"]
        escalated = bool(row["escalated"])
        blob = self._load_call_metrics_blob(row)
        from limen.safety.decision import SafetyDecision

        reasons = self._collect_safety_reasons(blob)
        evidence_refs = self._collect_evidence_refs(account_id, call_id)
        safety = (
            SafetyDecision(
                severity=Severity[risk],
                reasons=reasons,
                escalate=escalated,
            )
            if risk in Severity.__members__
            else None
        )
        call_metrics = blob.get("call") if isinstance(blob.get("call"), dict) else {}
        summary = build_call_summary(
            patient_alias=row["patient_alias"],
            procedure=row["procedure"],
            postoperative_day=row["postoperative_day"],
            state=clinical,
            safety=safety,
            evidence=evidence_refs,
            metrics={
                "call": call_metrics,
                "voice_latencies_ms": blob.get("voice_latencies_ms") or [],
                "voice_interruptions": blob.get("voice_interruptions") or 0,
                "turn_count": len(blob.get("turns") or []),
            },
        )
        if escalated and safety is not None:
            artifact = self._build_escalation_artifact(
                call_id=call_id,
                row=row,
                clinical=clinical,
                safety=safety,
                evidence_refs=evidence_refs,
            )
            summary["escalation_artifact"] = artifact
            blob["escalation_artifact"] = artifact
            self._traces.append(
                call_id=call_id,
                account_id=account_id,
                stage="escalation",
                event_type="escalation.artifact.persisted",
                label="Escalation artifact",
                risk=safety.severity.name,
                escalate=True,
                reasons=list(safety.reasons),
                payload=artifact,
            )

        finished = self._calls.finish_call(
            account_id=account_id,
            call_id=call_id,
            final_risk=risk,
            escalated=escalated,
            summary=summary,
            clinical_state=clinical,
            metrics=blob or None,
        )
        self._traces.append(
            call_id=call_id,
            account_id=account_id,
            stage="session_end",
            event_type="call.completed",
            label="Call finished",
            risk=risk,
            escalate=escalated,
        )
        return finished

    def summary(self, account_id: str, call_id: str) -> dict[str, Any] | None:
        return self._calls.get_summary_payload(account_id, call_id)

    def trace(self, account_id: str, call_id: str) -> dict[str, Any] | None:
        call = self._calls.get_call(account_id, call_id)
        if call is None:
            return None
        events = self._traces.list_events(account_id, call_id)
        row = self._calls.get_call_row(account_id, call_id)
        blob = self._load_call_metrics_blob(row) if row else {}
        call_metrics = blob.get("call")
        if not call_metrics:
            from limen.telemetry.aggregates import aggregate_from_trace_events

            call_metrics = aggregate_from_trace_events(events).model_dump(mode="json")
        conversation_debug = None
        raw_ctx = blob.get("conversation_context")
        if isinstance(raw_ctx, dict) and raw_ctx:
            try:
                conversation_debug = ConversationContext.model_validate(raw_ctx).debug_view()
            except Exception:
                conversation_debug = None
        return {
            "call_id": call_id,
            "events": events,
            "final_risk": call["final_risk"],
            "escalated": call["escalated"],
            "totals": call_metrics,
            "schema_version": 1,
            "conversation_debug": conversation_debug,
        }

    def mark_voice_interrupted(self, *, account_id: str, call_id: str) -> None:
        """Persist barge-in: keep meaning, mark assistant intent incomplete."""
        row = self._calls.get_call_row(account_id, call_id)
        if row is None:
            return
        blob = self._load_call_metrics_blob(row)
        ctx = self._load_conversation_context(blob, call_id=call_id)
        ctx = mark_interrupted(ctx)
        blob["conversation_context"] = ctx.model_dump(mode="json")
        blob["voice_interruptions"] = int(blob.get("voice_interruptions") or 0) + 1
        from limen.clinical.state import ClinicalState

        clinical = ClinicalState.model_validate_json(row["clinical_state_json"] or "{}")
        self._calls.update_runtime(
            account_id=account_id,
            call_id=call_id,
            clinical_state=clinical,
            final_risk=row["final_risk"],
            escalated=bool(row["escalated"]),
            metrics=blob,
        )
        self._traces.append(
            call_id=call_id,
            account_id=account_id,
            stage="conversation",
            event_type="conversation.response.interrupted",
            label="Assistant response interrupted",
            payload=ctx.debug_view(),
        )

    @staticmethod
    def _collect_safety_reasons(blob: dict[str, Any]) -> builtins.list[str]:
        reasons: builtins.list[str] = []
        last = blob.get("last_safety")
        if isinstance(last, dict):
            for reason in last.get("reasons") or []:
                if reason and str(reason) not in reasons:
                    reasons.append(str(reason))
        artifact = blob.get("escalation_artifact")
        if isinstance(artifact, dict):
            for reason in artifact.get("reasons") or []:
                if reason and str(reason) not in reasons:
                    reasons.append(str(reason))
        return reasons

    def _collect_evidence_refs(
        self, account_id: str, call_id: str
    ) -> builtins.list[EvidenceChunk]:
        """Rebuild evidence chunk refs from TRAZA retrieval events (no re-query)."""
        events = self._traces.list_events(account_id, call_id)
        seen: set[str] = set()
        chunks: builtins.list[EvidenceChunk] = []
        for event in events:
            if event.get("event_type") not in {
                "retrieval.evidence.selected",
                "retrieval",
            } and event.get("stage") != "retrieval":
                continue
            for item in event.get("evidence") or []:
                if not isinstance(item, dict):
                    continue
                chunk_id = str(item.get("chunk_id") or "")
                if not chunk_id or chunk_id in seen:
                    continue
                seen.add(chunk_id)
                try:
                    chunks.append(EvidenceChunk.model_validate(item))
                except Exception:
                    continue
            metrics = event.get("metrics") or {}
            if isinstance(metrics, dict):
                for chunk_id in metrics.get("selected_chunk_ids") or []:
                    cid = str(chunk_id)
                    if cid in seen:
                        continue
                    seen.add(cid)
                    docs = metrics.get("selected_document_ids") or []
                    chunks.append(
                        EvidenceChunk(
                            document_id=str(docs[0]) if docs else "unknown",
                            chunk_id=cid,
                            text="",
                            source_name="retrieved",
                            page=None,
                            score=0.0,
                        )
                    )
        return chunks

    @staticmethod
    def _build_escalation_artifact(
        *,
        call_id: str,
        row: Any,
        clinical: ClinicalState,
        safety: Any,
        evidence_refs: builtins.list[EvidenceChunk],
    ) -> dict[str, Any]:
        from datetime import UTC, datetime

        return {
            "call_id": call_id,
            "patient_alias": row["patient_alias"],
            "procedure": row["procedure"],
            "postoperative_day": row["postoperative_day"],
            "severity": safety.severity.name,
            "escalate": True,
            "reasons": list(safety.reasons),
            "timestamp": datetime.now(UTC).isoformat(),
            "findings": [
                {"name": f.name, "certainty": f.certainty.value, "notes": f.notes}
                for f in clinical.findings
            ],
            "evidence_references": [
                {
                    "document_id": c.document_id,
                    "chunk_id": c.chunk_id,
                    "source_name": c.source_name,
                    "page": c.page,
                }
                for c in evidence_refs
            ],
            "next_action": "Contactar atención médica de urgencia",
        }

    @staticmethod
    def _load_conversation_context(
        blob: dict[str, Any], *, call_id: str
    ) -> ConversationContext:
        raw = blob.get("conversation_context")
        if isinstance(raw, dict) and raw:
            try:
                ctx = ConversationContext.model_validate(raw)
                if not ctx.call_id:
                    ctx.call_id = call_id
                return ctx
            except Exception:
                pass
        return ConversationContext(call_id=call_id)

    @staticmethod
    def _load_call_metrics_blob(row: Any) -> dict[str, Any]:
        import json

        raw = row["metrics_json"] if row is not None else "{}"
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
