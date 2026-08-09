"""Conservative ASR repairs for common Spanish clinical mishearings.

Only high-confidence phrase/token swaps. Never invents symptoms that were
not phonetically close to what Whisper produced.
"""

from __future__ import annotations

import re

# (pattern, replacement) — applied in order; case-preserving via function.
_REPAIRS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bboletas\b", re.I), "muletas"),
    (re.compile(r"\bsomareos\b", re.I), "mareos"),
    (re.compile(r"\bson\s+mareos\b", re.I), "mareos"),
    (re.compile(r"\bfieles\b", re.I), "fiebres"),
    (re.compile(r"\bvalores\s+de\s+cabeza\b", re.I), "dolores de cabeza"),
    (re.compile(r"\bmejor\s+anotable\b", re.I), "mejora notable"),
    (re.compile(r"\bmejora\s+anotable\b", re.I), "mejora notable"),
    (re.compile(r"\bdobel[eé]\b", re.I), "duele"),
    (re.compile(r"\blia\s+bastante\b", re.I), "dolía bastante"),
    (re.compile(r"\banika\b", re.I), "Anikka"),
]

# Whisper initial prompt biases decoding toward postop Spanish (Colombia).
STT_INITIAL_PROMPT_ES = (
    "Seguimiento médico postoperatorio en español de Colombia. "
    "El paciente puede decir: dolor, fiebre, herida, muletas, mareos, "
    "escalofríos, temperatura, cirugía, medicación, tos, sangrado, "
    "náuseas, ansiedad, tristeza. "
    "Nombres posibles del asistente: Elena, Nikolas, Anikka, Alex."
)


def repair_transcript_text(text: str) -> str:
    """Apply conservative lexical repairs after Whisper normalization."""
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return ""

    def _preserve(match: re.Match[str], replacement: str) -> str:
        raw = match.group(0)
        if raw.isupper():
            return replacement.upper()
        if raw[0].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    out = cleaned
    for pattern, replacement in _REPAIRS:
        out = pattern.sub(lambda m, r=replacement: _preserve(m, r), out)
    return " ".join(out.split())
