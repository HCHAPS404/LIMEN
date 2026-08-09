"""Structured call summary builders."""

from __future__ import annotations

from typing import Any

from limen.clinical.state import ClinicalState
from limen.clinical.uncertainty import ClinicalCertainty
from limen.knowledge.contracts import EvidenceChunk
from limen.safety.decision import SafetyDecision


def summarize_state(state: ClinicalState) -> str:
    if not state.findings:
        return "No clinical findings recorded."
    parts = [f"{f.name}:{f.certainty.value}" for f in state.findings]
    return "; ".join(parts)


def build_call_summary(
    *,
    patient_alias: str,
    procedure: str | None,
    postoperative_day: int | None,
    state: ClinicalState,
    safety: SafetyDecision | None,
    evidence: list[EvidenceChunk],
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reported = [f.name for f in state.findings if f.certainty == ClinicalCertainty.KNOWN_ABNORMAL]
    unknown = [f.name for f in state.findings if f.certainty == ClinicalCertainty.UNKNOWN]
    conflicting = [f.name for f in state.findings if f.certainty == ClinicalCertainty.CONFLICTING]
    negative = [f.name for f in state.findings if f.certainty == ClinicalCertainty.KNOWN_NORMAL]
    risk = safety.severity.name if safety else None
    escalated = bool(safety and safety.escalate)
    metrics = metrics or {}
    raw_call = metrics.get("call")
    call_agg = raw_call if isinstance(raw_call, dict) else {}
    return {
        "patient": {
            "patient_id": patient_alias,
            "procedure": procedure,
            "postoperative_day": postoperative_day,
        },
        "reported_findings": reported,
        "negative_findings": negative,
        "unknown_findings": unknown,
        "conflicting_findings": conflicting,
        "open_questions": list(state.open_questions),
        "risk": risk,
        "escalated": escalated,
        "reasons": list(safety.reasons) if safety else [],
        "evidence": [chunk.model_dump(mode="json") for chunk in evidence],
        "uncertainties": {
            "unknown": unknown,
            "conflicting": conflicting,
            "open_questions": list(state.open_questions),
        },
        "call_duration_seconds": call_agg.get("duration_seconds"),
        "next_steps": (
            ["Contactar urgencias"]
            if escalated
            else ["Continuar observación", "Reevaluar si aparecen signos de alarma"]
        ),
        "metrics": metrics,
    }
