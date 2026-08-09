"""STT hallucination rejection for short echo / silence clips."""

from __future__ import annotations

from limen.voice.transcript_quality import is_likely_stt_hallucination


def test_rejects_adios_on_short_clip() -> None:
    assert is_likely_stt_hallucination("¡Adiós!", duration_ms=420) is True
    assert is_likely_stt_hallucination("Suscríbete!", duration_ms=600) is True


def test_keeps_real_goodbye_on_normal_clip() -> None:
    assert is_likely_stt_hallucination("Adiós", duration_ms=1200) is False
    assert is_likely_stt_hallucination("me voy", duration_ms=900) is False


def test_keeps_real_clinical_phrase() -> None:
    assert (
        is_likely_stt_hallucination(
            "Me duele la herida como un siete",
            duration_ms=1800,
            confidence=0.7,
        )
        is False
    )


def test_empty_is_hallucination() -> None:
    assert is_likely_stt_hallucination("  ", duration_ms=1000) is True
