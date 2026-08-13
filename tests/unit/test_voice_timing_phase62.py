"""Unit tests for voice timing invariants and SERVER_TTS_READY_PROXY naming."""

from __future__ import annotations

from limen.voice.timing_record import VoiceTurnTimingRecord


def test_proxy_includes_stt_when_speech_end_before_stt() -> None:
    r = VoiceTurnTimingRecord(sample_id="s1", turn_id="t1")
    r.speech_end = 1.0
    r.stt_start = 1.0
    r.stt_end = 2.0
    r.turn_processing_start = 2.0
    r.turn_processing_end = 3.0
    r.tts_start = 3.0
    r.tts_ready = 4.0
    assert r.validate_invariants()
    assert r.stt_ms == 1000.0
    assert r.server_tts_ready_proxy_ms == 3000.0
    assert r.server_tts_ready_proxy_ms >= r.stt_ms
    assert r.challenge_voice_e2e_ms is None


def test_invalid_when_proxy_excludes_stt() -> None:
    """PHASE 6.1 bug pattern: speech_end marked after STT."""
    r = VoiceTurnTimingRecord(sample_id="s1", turn_id="t1")
    r.speech_end = 2.0  # after STT
    r.stt_start = 1.0
    r.stt_end = 2.0
    r.tts_start = 2.0
    r.tts_ready = 3.0
    assert not r.validate_invariants()
    assert "speech_end>stt_start" in r.invalid_reasons or "SERVER_TTS_READY_PROXY<stt_ms" in (
        r.invalid_reasons
    )


def test_challenge_e2e_requires_playback() -> None:
    r = VoiceTurnTimingRecord(sample_id="s1", turn_id="t1")
    r.speech_end = 1.0
    r.stt_start = 1.1
    r.stt_end = 1.5
    r.turn_processing_start = 1.5
    r.turn_processing_end = 2.0
    r.tts_start = 2.0
    r.tts_ready = 2.5
    r.audio_received_browser = 2.6
    r.audio_playback_start = 2.7
    assert r.validate_invariants()
    assert abs((r.challenge_voice_e2e_ms or 0) - 1700.0) < 1e-6
    assert (r.challenge_voice_e2e_ms or 0) >= (r.stt_ms or 0)


def test_cross_clock_tts_ready_does_not_invalidate_browser_e2e() -> None:
    """Server tts_ready and browser playback_start are different clocks."""
    r = VoiceTurnTimingRecord(sample_id="s1", turn_id="t1")
    r.speech_end = 1.0
    r.stt_start = 1.1
    r.stt_end = 1.5
    r.turn_processing_start = 1.5
    r.turn_processing_end = 2.0
    r.tts_start = 2.0
    r.tts_ready = 9.0
    r.audio_received_browser = 2.6
    r.audio_playback_start = 2.7
    assert r.validate_invariants()
    assert r.valid
    assert abs((r.challenge_voice_e2e_ms or 0) - 1700.0) < 1e-6
