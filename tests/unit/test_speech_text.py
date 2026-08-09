"""Speech text prep and Piper PCM helpers (no subjective quality claims)."""

from __future__ import annotations

from limen.voice.providers.piper_tts import _apply_edge_fade, _join_pcm_chunks, _silence_pcm16
from limen.voice.speech_text import prepare_speech_text


def test_prepare_speech_text_scores_and_terminal_punct() -> None:
    assert prepare_speech_text("Anoto el dolor en 7/10") == "Anoto el dolor en 7 de 10."
    assert prepare_speech_text("Hola.") == "Hola."
    assert prepare_speech_text("") == ""


def test_pcm_silence_and_join_inserts_gap() -> None:
    a = b"\x01\x00" * 10
    b = b"\x02\x00" * 10
    joined = _join_pcm_chunks([a, b], sample_rate_hz=1000, sentence_silence_ms=10.0)
    silence = _silence_pcm16(sample_rate_hz=1000, duration_ms=10.0)
    assert silence in joined
    assert joined.startswith(a)
    assert joined.endswith(b)


def test_edge_fade_shortens_edges() -> None:
    # Constant amplitude; fade should reduce first/last samples.
    pcm = (b"\x00\x40") * 2000
    faded = _apply_edge_fade(pcm, sample_rate_hz=1000, fade_ms=10.0)
    assert len(faded) == len(pcm)
    assert faded[:2] != pcm[:2] or faded[-2:] != pcm[-2:]
