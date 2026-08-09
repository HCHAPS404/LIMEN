"""PHASE 6 voice unit tests — codec, VAD, latency, stub providers."""

from __future__ import annotations

import wave
from io import BytesIO

import pytest

from limen.config.settings import ApplicationSettings
from limen.telemetry.aggregates import aggregate_call_metrics
from limen.voice.audio_codec import (
    AudioFormatError,
    normalize_transcript_text,
    silence_wav,
    wav_to_mono_16k_float32,
    write_pcm16_wav,
)
from limen.voice.pipeline import compute_voice_response_latency_ms
from limen.voice.stt import StubSTTProvider, build_stt_provider
from limen.voice.tts import StubTTSProvider, build_tts_provider
from limen.voice.vad import EndpointConfig, FrameEndpointer


def test_wav_roundtrip_and_duration() -> None:
    pcm = b"\x00\x00" * 1600  # 100ms @ 16kHz mono
    wav = write_pcm16_wav(pcm)
    samples, meta = wav_to_mono_16k_float32(wav)
    assert len(samples) == 1600
    assert meta["duration_ms"] == pytest.approx(100.0, rel=0.05)


def test_invalid_wav_raises() -> None:
    with pytest.raises(AudioFormatError):
        wav_to_mono_16k_float32(b"not-a-wav")


def test_normalize_preserves_negation() -> None:
    assert normalize_transcript_text("  no tengo   fiebre  ") == "no tengo fiebre"
    assert "no " in normalize_transcript_text("no tengo fiebre")


def test_endpointing_min_max_and_false_trigger() -> None:
    ep = FrameEndpointer(
        EndpointConfig(
            speech_threshold=0.05,
            silence_threshold=0.02,
            min_speech_frames=2,
            silence_hangover_frames=3,
            min_utterance_frames=5,
            max_utterance_frames=20,
        )
    )
    # False trigger: brief speech then silence before min frames.
    assert ep.push(0.1).is_speech is False
    assert ep.push(0.1).is_speech is True
    for _ in range(2):
        ep.push(0.0)
    decision = ep.push(0.0)
    assert decision.should_close_utterance is False
    assert decision.reason == "false_trigger"

    ep.reset()
    for _ in range(2):
        ep.push(0.2)
    for _ in range(6):
        ep.push(0.2)
    for _ in range(3):
        d = ep.push(0.0)
    assert d.should_close_utterance is True
    assert d.reason == "silence_hangover"


def test_voice_response_latency_math() -> None:
    assert compute_voice_response_latency_ms(
        speech_end_monotonic=1.0,
        agent_audio_started_monotonic=1.25,
    ) == pytest.approx(250.0)
    assert (
        compute_voice_response_latency_ms(
            speech_end_monotonic=None,
            agent_audio_started_monotonic=1.0,
        )
        is None
    )
    assert (
        compute_voice_response_latency_ms(
            speech_end_monotonic=2.0,
            agent_audio_started_monotonic=1.0,
        )
        is None
    )


def test_aggregate_voice_percentiles() -> None:
    empty = aggregate_call_metrics([])
    assert empty.voice_latency_status == "not_implemented"
    few = aggregate_call_metrics([], voice_latencies_ms=[100.0, 200.0])
    assert few.voice_latency_status == "insufficient_samples"
    assert few.voice_latency_sample_count == 2
    many = aggregate_call_metrics([], voice_latencies_ms=[100.0, 200.0, 300.0, 400.0])
    assert many.voice_latency_status == "measured"
    assert many.voice_latency_p50_ms is not None
    assert many.voice_latency_p95_ms is not None


async def test_stub_stt_tts_contracts() -> None:
    stt = StubSTTProvider()
    tts = StubTTSProvider()
    wav = silence_wav(duration_ms=300)
    transcript = await stt.transcribe(wav)
    assert transcript.text
    assert transcript.provider == "stub"
    audio = await tts.synthesize("Hola, gracias por contarme.", "default")
    assert audio.mime_type == "audio/wav"
    assert audio.audio[:4] == b"RIFF"
    with wave.open(BytesIO(audio.audio), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2


def test_build_providers_stub_and_reject_unknown() -> None:
    settings = ApplicationSettings(STT_PROVIDER="stub", TTS_PROVIDER="stub", _env_file=None)
    assert build_stt_provider(settings).provider_name == "stub"  # type: ignore[attr-defined]
    assert build_tts_provider(settings).provider_name == "stub"  # type: ignore[attr-defined]
    with pytest.raises(ValueError):
        build_stt_provider(ApplicationSettings(STT_PROVIDER="twilio", _env_file=None))
