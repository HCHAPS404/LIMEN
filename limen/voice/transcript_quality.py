"""Reject likely STT hallucinations on short / empty acoustic segments."""

from __future__ import annotations

import re
import unicodedata

# Common Whisper garbage on silence, music beds, or speaker echo.
_HALLUCINATION_EXACT: frozenset[str] = frozenset(
    {
        "adios",
        "adiós",
        "hola",
        "hello",
        "thanks for watching",
        "thank you for watching",
        "subscribe",
        "suscribete",
        "suscríbete",
        "subtitles by",
        "subtitulos",
        "subtítulos",
        "am",
        "um",
        "uh",
        "mm",
        "mmm",
        ".",
        "...",
    }
)

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _fold(text: str) -> str:
    raw = unicodedata.normalize("NFKD", (text or "").strip())
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = _PUNCT_RE.sub("", raw.casefold())
    return " ".join(raw.split())


def is_likely_stt_hallucination(
    text: str,
    *,
    duration_ms: float | None,
    confidence: float | None = None,
) -> bool:
    """True when the transcript is probably not real patient speech.

    Short clips (< ~900 ms) that collapse to known one-token Whisper fillers
    (e.g. «¡Adiós!», «Suscríbete!») must not become turns.
    """
    folded = _fold(text)
    if not folded:
        return True

    duration = float(duration_ms) if duration_ms is not None else None
    short = duration is not None and duration < 900.0

    if folded in _HALLUCINATION_EXACT:
        # Only reject known fillers on short/noisy clips — real "adiós"/"hola"
        # with normal utterance length must remain patient speech.
        return bool(short)

    return False
