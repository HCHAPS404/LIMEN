"""Deterministic post-generation validator for patient-facing LLM text.

Rejects high-risk contradictions with the authoritative SafetyDecision.
Does not attempt full clinical NLP.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from limen.knowledge.contracts import EvidenceChunk
from limen.safety.decision import SafetyDecision, Severity

_DOWNGRADE_OK_PATTERNS = (
    re.compile(r"\btodo (parece |está )?normal\b", re.I),
    re.compile(r"\bno hay (ningún )?riesgo\b", re.I),
    re.compile(r"\bpuede(s)? seguir en casa\b", re.I),
    re.compile(r"\bsin (ninguna )?preocupaci[oó]n\b", re.I),
    re.compile(r"\bno es (nada )?grave\b", re.I),
    re.compile(r"\best[aá] (todo )?bien\b", re.I),
    re.compile(r"\bignore (previous|all|system) instructions\b", re.I),
    re.compile(r"\beverything is fine\b", re.I),
)

_META_FORBIDDEN = (
    re.compile(r"\bcomo (un )?modelo de lenguaje\b", re.I),
    re.compile(r"\bsystem prompt\b", re.I),
    re.compile(r"\binstrucciones (del )?sistema\b", re.I),
    re.compile(r"\bchain[- ]of[- ]thought\b", re.I),
    re.compile(r"\bignore (las )?instrucciones\b", re.I),
    re.compile(r"\bSYSTEM OVERRIDE\b", re.I),
)

_CITATION_CLAIM = (
    re.compile(r"\bdoi:\s*\S+", re.I),
    re.compile(r"\bhttps?://\S+", re.I),
    re.compile(r"\bseg[uú]n (el|la|un|una) (estudio|art[ií]culo|gu[ií]a|paper)\b", re.I),
    re.compile(r"\[\d+\]"),
)

_MEDICATION = (
    re.compile(
        r"\b(ibuprofeno|paracetamol|acetaminof[eé]n|amoxicilina|morfina|"
        r"tramadol|diclofenaco|omeprazol|warfarina|insulina)\b",
        re.I,
    ),
    re.compile(r"\b\d+\s?(mg|mcg|ml|ui)\b", re.I),
)

_ESCALATION_MARKERS = (
    re.compile(r"\burgenc", re.I),
    re.compile(r"\bemergenc", re.I),
    re.compile(r"\bcontacte atenci[oó]n m[eé]dica\b", re.I),
    re.compile(r"\bllamar?\b.*\b(m[eé]dic|urgenc|911|123)\b", re.I),
    re.compile(r"\briesgo\b", re.I),
)


@dataclass
class ValidationResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    generated_response_validated: bool = False

    @property
    def fallback_reason(self) -> str | None:
        if self.ok:
            return None
        return ";".join(self.reasons) if self.reasons else "validation_failed"


def validate_patient_response(
    text: str,
    *,
    safety: SafetyDecision,
    evidence: list[EvidenceChunk] | None = None,
) -> ValidationResult:
    evidence = evidence or []
    reasons: list[str] = []
    cleaned = (text or "").strip()

    if len(cleaned) < 8:
        reasons.append("empty_or_too_short")
        return ValidationResult(ok=False, reasons=reasons, generated_response_validated=False)

    for pat in _META_FORBIDDEN:
        if pat.search(cleaned):
            reasons.append("forbidden_meta_language")
            break

    if safety.escalate or safety.severity >= Severity.RED:
        if any(p.search(cleaned) for p in _DOWNGRADE_OK_PATTERNS):
            reasons.append("red_downgrade_contradiction")
        if not any(p.search(cleaned) for p in _ESCALATION_MARKERS):
            reasons.append("escalation_not_communicated")

    if safety.severity >= Severity.YELLOW and not safety.escalate and any(
        p.search(cleaned)
        for p in (
            _DOWNGRADE_OK_PATTERNS[0],
            _DOWNGRADE_OK_PATTERNS[1],
            _DOWNGRADE_OK_PATTERNS[5],
            _DOWNGRADE_OK_PATTERNS[7],
        )
    ):
        reasons.append("yellow_downgrade_contradiction")

    allowed_sources = {c.source_name.lower() for c in evidence if c.source_name}
    evidence_blob = " ".join(c.text for c in evidence).lower()
    for pat in _CITATION_CLAIM:
        match = pat.search(cleaned)
        if not match:
            continue
        claim = match.group(0).lower()
        if any(src and src in claim for src in allowed_sources):
            continue
        if claim.startswith("http") and any(claim in c.text.lower() for c in evidence):
            continue
        reasons.append("invented_citation")
        break

    for pat in _MEDICATION:
        match = pat.search(cleaned)
        if not match:
            continue
        token = match.group(0).lower()
        if token in evidence_blob:
            continue
        reasons.append("unsupported_medication_or_dose")
        break

    ok = not reasons
    return ValidationResult(
        ok=ok,
        reasons=reasons,
        generated_response_validated=ok,
    )
