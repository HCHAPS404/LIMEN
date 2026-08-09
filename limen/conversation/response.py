"""Patient-facing response generation.

Severity is never set here. Authoritative SafetyDecision is immutable input.
LLM drafts phrasing only; deterministic validator + templates are the safety net.
"""

from __future__ import annotations

from typing import Any

from limen.clinical.state import ClinicalState
from limen.clinical.uncertainty_analysis import UncertaintyReport
from limen.conversation.context import ConversationContext
from limen.conversation.continuity import has_excessive_generic_opener, is_near_duplicate
from limen.conversation.response_templates import (
    ESCALATION_TEMPLATE,
    EVIDENCE_TEMPLATE,
    FALLBACK_TEMPLATE,
    deterministic_patient_reply,
)
from limen.conversation.response_validator import validate_patient_response
from limen.intelligence.contracts import LLMProvider, LLMRequest
from limen.intelligence.llm_status import get_llm_runtime_status
from limen.intelligence.prompts.patient_response import build_patient_response_messages
from limen.knowledge.contracts import EvidenceChunk
from limen.safety.decision import SafetyDecision, Severity

__all__ = [
    "ESCALATION_TEMPLATE",
    "FALLBACK_TEMPLATE",
    "EVIDENCE_TEMPLATE",
    "build_assistant_response",
]


async def build_assistant_response(
    *,
    user_text: str,
    safety: SafetyDecision,
    evidence: list[EvidenceChunk],
    open_questions: list[str],
    llm: LLMProvider | None,
    clinical_state: ClinicalState | None = None,
    uncertainty: UncertaintyReport | None = None,
    conversation: ConversationContext | None = None,
    force_degraded: bool | None = None,
) -> tuple[str, int, int | None, int | None, dict[str, Any]]:
    """Return (text, llm_calls, prompt_tokens, completion_tokens, meta)."""
    status = get_llm_runtime_status()
    degraded = bool(status.degraded_mode) if force_degraded is None else force_degraded
    previous = conversation.previous_assistant_response if conversation else None

    def _template() -> str:
        return deterministic_patient_reply(
            safety=safety,
            clinical_state=clinical_state,
            evidence=evidence,
            open_questions=open_questions,
            conversation=conversation,
        )

    if safety.escalate or safety.severity >= Severity.RED:
        text = _template()
        return (
            text,
            0,
            None,
            None,
            {
                "used_llm": False,
                "generated_response_validated": True,
                "fallback": True,
                "fallback_reason": "authoritative_red_or_escalate_template",
                "degraded_mode": degraded,
                "response_source": "template",
            },
        )

    if llm is None or degraded:
        text = _template()
        return (
            text,
            0,
            None,
            None,
            {
                "used_llm": False,
                "generated_response_validated": True,
                "fallback": True,
                "fallback_reason": "degraded_llm_mode" if degraded else "llm_unavailable",
                "degraded_mode": degraded,
                "response_source": "template",
            },
        )

    async def _generate(*, avoid_repeat_of: str | None) -> tuple[str, Any, dict[str, Any]]:
        system, prompt = build_patient_response_messages(
            user_text=user_text,
            safety=safety,
            clinical_state=clinical_state,
            uncertainty=uncertainty,
            evidence=evidence,
            open_questions=open_questions,
            conversation=conversation,
            avoid_repeat_of=avoid_repeat_of,
        )
        response = await llm.generate_text(
            LLMRequest(
                prompt=prompt,
                system=system,
                temperature=0.2,
                max_tokens=120,
                metadata={"purpose": "patient_response"},
            )
        )
        text = _sanitize_llm_text(response.text)
        meta = {
            "provider": response.provider or getattr(llm, "provider_name", "llm"),
            "model": response.model,
            "latency_ms": response.latency_ms,
            "generation_ms": response.generation_ms,
            "time_to_first_token_ms": response.time_to_first_token_ms,
            "finish_reason": response.finish_reason,
            "provider_usage": {
                "provider": response.provider or getattr(llm, "provider_name", "llm"),
                "model": response.model,
                "input_tokens": response.prompt_tokens,
                "output_tokens": response.completion_tokens,
                "latency_ms": response.latency_ms,
                "generation_ms": response.generation_ms,
                "time_to_first_token_ms": response.time_to_first_token_ms,
                "finish_reason": response.finish_reason,
                "llm_calls": 1,
            },
        }
        return text, response, meta

    try:
        text, response, provider_meta = await _generate(avoid_repeat_of=None)
    except Exception as exc:
        status.mark_provider_error(f"{type(exc).__name__}:{exc}")
        text = _template()
        return (
            text,
            0,
            None,
            None,
            {
                "error": True,
                "error_category": "llm_provider_failure",
                "safe_message": "LLM provider failed; used template fallback",
                "provider": getattr(llm, "provider_name", type(llm).__name__),
                "exception_type": type(exc).__name__,
                "used_llm": False,
                "generated_response_validated": True,
                "fallback": True,
                "fallback_reason": f"provider_error:{type(exc).__name__}",
                "degraded_mode": degraded,
                "response_source": "template",
            },
        )

    llm_calls = 1
    prompt_tokens = response.prompt_tokens
    completion_tokens = response.completion_tokens
    novelty_retry = False

    # One novelty retry only — never loop.
    if previous and (
        is_near_duplicate(text, previous)
        or has_excessive_generic_opener(text, previous)
    ):
        novelty_retry = True
        try:
            text2, response2, provider_meta = await _generate(avoid_repeat_of=previous)
            llm_calls = 2
            if response2.prompt_tokens is not None or prompt_tokens is not None:
                prompt_tokens = (prompt_tokens or 0) + (response2.prompt_tokens or 0)
            if response2.completion_tokens is not None or completion_tokens is not None:
                completion_tokens = (completion_tokens or 0) + (
                    response2.completion_tokens or 0
                )
            if text2 and not is_near_duplicate(text2, previous):
                text = text2
            else:
                text = _template()
                provider_meta["fallback"] = True
                provider_meta["fallback_reason"] = "novelty_retry_still_duplicate"
        except Exception:
            text = _template()
            provider_meta["fallback"] = True
            provider_meta["fallback_reason"] = "novelty_retry_failed"

    validation = validate_patient_response(text, safety=safety, evidence=evidence)
    if not validation.ok or not text:
        text = _template()
        return (
            text,
            llm_calls,
            prompt_tokens,
            completion_tokens,
            {
                **provider_meta,
                "used_llm": True,
                "generated_response_validated": False,
                "fallback": True,
                "fallback_reason": validation.fallback_reason or "empty_after_sanitize",
                "validation_reasons": list(validation.reasons),
                "degraded_mode": degraded,
                "novelty_retry": novelty_retry,
                "response_source": "template",
            },
        )

    # Template fallback if still near-duplicate after retry (non-RED path).
    if previous and is_near_duplicate(text, previous):
        text = _template()
        return (
            text,
            llm_calls,
            prompt_tokens,
            completion_tokens,
            {
                **provider_meta,
                "used_llm": True,
                "generated_response_validated": True,
                "fallback": True,
                "fallback_reason": "deterministic_after_duplicate",
                "degraded_mode": degraded,
                "novelty_retry": novelty_retry,
                "response_source": "template",
            },
        )

    return (
        text,
        llm_calls,
        prompt_tokens,
        completion_tokens,
        {
            **provider_meta,
            "used_llm": True,
            "generated_response_validated": True,
            "fallback": bool(provider_meta.get("fallback")),
            "fallback_reason": provider_meta.get("fallback_reason"),
            "degraded_mode": degraded,
            "novelty_retry": novelty_retry,
            "response_source": "llm",
        },
    )


def _sanitize_llm_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("[stub:"):
        marker = "Escribe solo la respuesta breve para el paciente:"
        if marker in text:
            text = text.split(marker, 1)[-1].strip()
        else:
            return ""
    text = " ".join(text.split())
    if len(text) > 320:
        text = text[:317].rstrip() + "…"
    if len(text) < 8:
        return ""
    return text
