"""Uncertainty analysis over ClinicalState — no LLM, no case IDs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from limen.clinical.state import ClinicalState, Finding
from limen.clinical.uncertainty import ClinicalCertainty

# Generic follow-ups keyed by finding name. Never challenge-case specific.
_FOLLOWUPS: dict[str, str] = {
    "pain": "¿Cómo evoluciona el dolor y con qué intensidad?",
    "pain_severity": "",  # informational finding — not a question source
    "fever": "¿Qué temperatura ha medido y desde cuándo?",
    "wound": "¿Cómo se ve la herida: enrojecimiento, secreción o apertura?",
    "wound_heat": "¿La herida sigue caliente o ha cambiado el enrojecimiento?",
    "bleeding": "¿Cuánta sangre ha visto y con qué frecuencia?",
    "breathing": "¿La falta de aire empeora en reposo o al caminar?",
    "nausea": "¿Las náuseas le impiden beber o tomar la medicación?",
}

# When severity is already known, prefer course over intensity re-ask.
_PAIN_COURSE_FOLLOWUP = "¿El dolor sigue igual, mejora o empeora?"


class UncertaintyReport(BaseModel):
    """Explicit unresolved clinical questions derived from state certainty."""

    unresolved: list[str] = Field(default_factory=list)
    conflicting: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    should_retrieve: bool = False


def analyze_uncertainty(state: ClinicalState) -> UncertaintyReport:
    """Classify findings and propose follow-up questions without inventing normals."""
    conflicting = [
        f.name for f in state.findings if f.certainty == ClinicalCertainty.CONFLICTING
    ]
    unknown = [
        f.name for f in state.findings if f.certainty == ClinicalCertainty.UNKNOWN
    ]
    abnormal = [
        f.name for f in state.findings if f.certainty == ClinicalCertainty.KNOWN_ABNORMAL
    ]
    finding_names_set = {f.name for f in state.findings}
    has_pain_severity = "pain_severity" in finding_names_set

    unresolved: list[str] = []
    for finding in state.findings:
        if finding.certainty == ClinicalCertainty.KNOWN_NORMAL:
            continue
        if finding.name == "pain_severity":
            continue
        if finding.certainty in {
            ClinicalCertainty.UNKNOWN,
            ClinicalCertainty.CONFLICTING,
            ClinicalCertainty.KNOWN_ABNORMAL,
        }:
            if finding.name == "pain" and has_pain_severity:
                question = _PAIN_COURSE_FOLLOWUP
            else:
                question = _FOLLOWUPS.get(
                    finding.name,
                    f"¿Puede precisar más detalles sobre {finding.name}?",
                )
            if not question:
                continue
            if question not in unresolved:
                unresolved.append(question)

    # Keep prior open questions that still apply; do not drop them silently.
    for prior in state.open_questions:
        if has_pain_severity and "intensidad" in prior.casefold():
            continue
        if prior not in unresolved:
            unresolved.append(prior)

    should_retrieve = bool(abnormal or unknown or conflicting or unresolved)
    return UncertaintyReport(
        unresolved=unresolved,
        conflicting=conflicting,
        unknown=unknown,
        should_retrieve=should_retrieve,
    )


def apply_uncertainty(
    state: ClinicalState,
    report: UncertaintyReport,
) -> ClinicalState:
    """Return a copy of state with open_questions from the uncertainty report."""
    updated = state.model_copy(deep=True)
    updated.open_questions = list(report.unresolved)
    return updated


def finding_names(findings: list[Finding]) -> list[str]:
    return [f.name for f in findings]
