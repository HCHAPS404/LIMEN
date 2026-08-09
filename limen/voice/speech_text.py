"""Prepare patient-facing text for spoken TTS without inventing clinical content."""

from __future__ import annotations

import re

_SLASH_SCORE = re.compile(r"\b(\d{1,2})\s*/\s*(\d{1,2})\b")
_MULTI_SPACE = re.compile(r"\s+")
_DENSE_PUNCT = re.compile(r"([.!?]){2,}")

# Long adverbs that Piper often mangles mid-word — swap for speakable synonyms.
_SPEAKABLE_SWAPS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsignificativamente\b", re.I), "de forma notable"),
    (re.compile(r"\baproximadamente\b", re.I), "más o menos"),
    (re.compile(r"\binmediatamente\b", re.I), "de inmediato"),
]


def prepare_speech_text(text: str) -> str:
    """Normalize phrasing so Piper can speak more naturally.

    Does not add clinical claims — only pronunciation-friendly rewrites.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    cleaned = cleaned.replace("…", ".")
    cleaned = _SLASH_SCORE.sub(r"\1 de \2", cleaned)
    for pattern, replacement in _SPEAKABLE_SWAPS:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = _DENSE_PUNCT.sub(r"\1", cleaned)
    cleaned = cleaned.replace(" ,", ",").replace(" .", ".")
    cleaned = _MULTI_SPACE.sub(" ", cleaned).strip()
    # Ensure terminal punctuation for a cleaner final phoneme.
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned
