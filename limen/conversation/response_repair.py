"""Repair / detect broken patient-facing LLM drafts before TTS.

Deterministic only — does not invent clinical claims.
"""

from __future__ import annotations

import re

_SENTENCE_END = re.compile(r"[.!?…][\"'»)]*\s*$")

# Mid-generation cuts frequently seen with Phi / small max_tokens.
_TRUNCATED_STEM = re.compile(
    r"\b("
    r"significativ\w*"
    r"|recuperaci\w*"
    r"|documentaci\w*"
    r"|inflamaci\w*"
    r"|recomend\w*"
    r"|seguimient\w*"
    r"|postoperat\w*"
    r"|temperatur\w*"
    r")\b",
    re.IGNORECASE,
)

_COMPLETE_FORMS = frozenset(
    {
        "significativamente",
        "significativo",
        "significativa",
        "significativos",
        "significativas",
        "recuperacion",
        "recuperación",
        "documentacion",
        "documentación",
        "inflamacion",
        "inflamación",
        "recomendacion",
        "recomendación",
        "recomendaciones",
        "seguimiento",
        "postoperatorio",
        "postoperatoria",
        "postoperatorios",
        "postoperatorias",
        "temperatura",
        "temperaturas",
    }
)

# "Estoy Anikka" is ungrammatical identity; Piper also trips on it.
_ESTOY_NAME = re.compile(
    r"\bEstoy\s+(Elena|Anikka|Nikolas|Alex|LIMEN)\b",
    re.IGNORECASE,
)

_ASSISTANT_NAMES = ("elena", "anikka", "anika", "nikolas", "alex", "limen")


def _last_word(text: str) -> str:
    token = re.split(r"\s+", text.strip())[-1]
    return re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", "", token)


def looks_truncated_draft(text: str) -> bool:
    """True when the draft likely ends mid-word or mid-clause."""
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return True
    last = _last_word(cleaned)
    if not last:
        return True
    folded = last.casefold()
    # Explicit mangled cut seen in production: significativs
    if folded.endswith("tivs") or folded in {"significativs", "significativ"}:
        return True
    if _TRUNCATED_STEM.fullmatch(last) and folded not in _COMPLETE_FORMS:
        return True
    # No terminal punctuation and last token looks like a stump.
    if not _SENTENCE_END.search(cleaned):
        if len(folded) <= 2:
            return True
        if (
            len(folded) >= 8
            and folded.endswith(("tiv", "ativ", "cion"))
            and folded not in _COMPLETE_FORMS
        ):
            return True
    return False


def trim_to_last_complete_sentence(text: str) -> str:
    """Drop a trailing incomplete clause when a prior sentence exists."""
    cleaned = " ".join((text or "").strip().split())
    if not cleaned or not looks_truncated_draft(cleaned):
        return cleaned
    best = -1
    for sep in (". ", "? ", "! ", "… "):
        idx = cleaned.rfind(sep)
        if idx > best:
            best = idx
    if best >= 12:
        return cleaned[: best + 1].strip()
    return ""


def strip_assistant_patient_vocative(text: str) -> str:
    """Remove mistaken patient vocatives that reuse the assistant persona name.

    Rejects drafts that still address the patient as Elena/Anikka/… after strip
    would leave nonsense — callers should validate and fallback.
    """
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return ""
    # Drop trailing ", Anikka" / "hoy, Anikka" style slips.
    cleaned = re.sub(
        r",\s*(?:elena|anikka|anika|nikolas|nicolas|alex)\b",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        r"\bse[nñ]or(?:a)?\s+(?:elena|anikka|anika|nikolas|nicolas|alex)\b",
        "",
        cleaned,
        flags=re.I,
    )
    return " ".join(cleaned.split()).strip()


def repair_identity_phrasing(text: str) -> str:
    """Fix common Phi identity slips without changing clinical content."""
    fixed = _ESTOY_NAME.sub(lambda m: f"Soy {m.group(1)}", text or "")
    return strip_assistant_patient_vocative(fixed)


def mentions_assistant_name(text: str) -> bool:
    folded = (text or "").casefold()
    return any(name in folded for name in _ASSISTANT_NAMES)
