"""Deterministic post-generation validator for patient-facing LLM text.

Rejects high-risk contradictions with the authoritative SafetyDecision.
Does not attempt full clinical NLP.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from limen.conversation.response_repair import looks_truncated_draft
from limen.conversation.session_intent import is_assistant_persona_name
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

# Voice path uses usted; informal tú drafts sound robotic when mixed with clinical tone.
_INFORMAL_ADDRESS = (
    re.compile(r"\b(tú|ti|contigo)\b", re.I),
    re.compile(r"\b(puedes|cuéntame|cuentame|dime|estás|estas)\b", re.I),
    re.compile(r"\bte\s+(sientes|duele|gustaría|gustaria|recomiendo)\b", re.I),
    re.compile(r"\btu\s+(dolor|herida|fiebre|recuperaci)", re.I),
)

_FAKE_CAPABILITY = (
    re.compile(r"\bprogramar\s+(una\s+)?cita\b", re.I),
    re.compile(r"\bagendar\s+(una\s+)?cita\b", re.I),
    re.compile(r"\bseguimiento\s+telef[oó]nico\b", re.I),
    re.compile(r"\bllamar[eé]\s+a\s+su\s+m[eé]dico\b", re.I),
)

_ESTOY_ASSISTANT = re.compile(
    r"\bestoy\s+(elena|anikka|nikolas|alex|limen)\b",
    re.I,
)

# Addressing the patient with the assistant's own persona name.
_ASSISTANT_AS_PATIENT = re.compile(
    r"(?:"
    r",\s*(elena|anikka|anika|nikolas|nicolas|alex)\b"
    r"|\bse[nñ]or(?:a)?\s+(elena|anikka|anika|nikolas|nicolas|alex)\b"
    r"|\b(elena|anikka|anika|nikolas|nicolas|alex)\s*,"
    r"|\b(elena|anikka|anika|nikolas|nicolas|alex)\s*[.!?…]?\s*$"
    r"|\bhoy\s*,\s*(elena|anikka|anika|nikolas|nicolas|alex)\b"
    r")",
    re.I,
)

_STRIP_ASSISTANT_VOCATIVE = re.compile(
    r"(?:,\s*)?\b(elena|anikka|anika|nikolas|nicolas|alex)\b(?=\s*[.!?,]|$)",
    re.I,
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


def _third_person_about_patient(text: str, display_name: str) -> bool:
    """Detect narration about the patient instead of addressing them."""
    name = (display_name or "").strip()
    if len(name) < 2:
        return False
    escaped = re.escape(name)
    patterns = (
        re.compile(rf"entiendo\s+que\s+{escaped}\s+ha\b", re.I),
        re.compile(rf"\b{escaped}\s+ha\s+\w+", re.I),
        re.compile(rf"\b{escaped}\s+ha\s+contactado\b", re.I),
        re.compile(rf"\b{escaped}\s+ha\s+agradecido\b", re.I),
        re.compile(rf"\b{escaped}\s+se\s+ha\s+(comunicado|puesto)\b", re.I),
    )
    return any(p.search(text) for p in patterns)


# Slash form or titled proper name when no session name was provided.
_INVENTED_VOCATIVE = re.compile(
    r"\bse[nñ]or\s*/\s*se[nñ]ora\b"
    r"|\bse[nñ]or(?:a)?\s+[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{1,23}\b",
    re.UNICODE,
)


def _invented_patient_name(text: str, display_name: str | None) -> bool:
    """True when the reply uses a titled name that is not in this call's context."""
    known = (display_name or "").strip()
    if known:
        # Allow the session name; still reject the literal slash form.
        return bool(re.search(r"\bse[nñ]or\s*/\s*se[nñ]ora\b", text, re.I))
    return _INVENTED_VOCATIVE.search(text) is not None


def validate_patient_response(
    text: str,
    *,
    safety: SafetyDecision,
    evidence: list[EvidenceChunk] | None = None,
    patient_display_name: str | None = None,
    assistant_display_name: str | None = None,
) -> ValidationResult:
    evidence = evidence or []
    reasons: list[str] = []
    cleaned = (text or "").strip()

    if len(cleaned) < 8:
        reasons.append("empty_or_too_short")
        return ValidationResult(ok=False, reasons=reasons, generated_response_validated=False)

    if looks_truncated_draft(cleaned):
        reasons.append("truncated_or_broken_word")

    if _ESTOY_ASSISTANT.search(cleaned):
        reasons.append("ungrammatical_assistant_identity")

    if _ASSISTANT_AS_PATIENT.search(cleaned):
        reasons.append("assistant_name_used_as_patient")

    if assistant_display_name and is_assistant_persona_name(assistant_display_name):
        # Explicit vocative of the live persona toward the patient.
        escaped = re.escape(assistant_display_name.strip())
        if re.search(rf",\s*{escaped}\b", cleaned, re.I) or re.search(
            rf"\bse[nñ]or(?:a)?\s+{escaped}\b", cleaned, re.I
        ):
            reasons.append("assistant_name_used_as_patient")

    for pat in _INFORMAL_ADDRESS:
        if pat.search(cleaned):
            reasons.append("informal_tu_address")
            break

    for pat in _FAKE_CAPABILITY:
        if pat.search(cleaned):
            reasons.append("unsupported_booking_or_callback_offer")
            break

    for pat in _META_FORBIDDEN:
        if pat.search(cleaned):
            reasons.append("forbidden_meta_language")
            break

    if patient_display_name and _third_person_about_patient(cleaned, patient_display_name):
        reasons.append("third_person_patient_narration")

    if _invented_patient_name(cleaned, patient_display_name):
        reasons.append("invented_or_stale_patient_name")

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
