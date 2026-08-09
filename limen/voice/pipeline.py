"""Voice turn helpers with challenge-critical timing marks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from limen.telemetry.timing import StageTimer
from limen.voice.contracts import AudioResult, STTProvider, Transcript, TTSProvider


@dataclass
class VoiceTurnTiming:
    marks: dict[str, float]
    stt_ms: float | None
    tts_ms: float | None
    # Local synthesis completion mark (not browser playback).
    tts_ready_ms: float | None
    first_audio_ms: float | None = None
    voice_response_latency_ms: float | None = None
    extras: dict[str, Any] = field(default_factory=dict)


async def transcribe_with_timing(
    stt: STTProvider,
    audio: bytes,
    *,
    language: str = "es",
    speech_end_monotonic: float | None = None,
) -> tuple[Transcript, VoiceTurnTiming]:
    """Transcribe audio. Prefer client speech_end_monotonic when provided."""
    timer = StageTimer()
    if speech_end_monotonic is not None:
        timer.marks["speech_end"] = float(speech_end_monotonic)
    else:
        timer.mark("speech_end")
    timer.mark("stt_start")
    transcript = await stt.transcribe(audio, language=language)
    timer.mark("stt_end")
    return transcript, VoiceTurnTiming(
        marks=dict(timer.marks),
        stt_ms=timer.elapsed_ms("stt_start", "stt_end"),
        tts_ms=None,
        tts_ready_ms=None,
        extras={"speech_end_source": "client" if speech_end_monotonic is not None else "server"},
    )


async def synthesize_with_timing(
    tts: TTSProvider,
    text: str,
    *,
    voice: str,
) -> tuple[AudioResult, VoiceTurnTiming]:
    from limen.voice.speech_text import prepare_speech_text

    spoken = prepare_speech_text(text)
    timer = StageTimer()
    timer.mark("tts_start")
    audio = await tts.synthesize(spoken, voice)
    timer.mark("tts_end")
    # Synthesis ready ≠ browser first audible sample.
    return audio, VoiceTurnTiming(
        marks=dict(timer.marks),
        stt_ms=None,
        tts_ms=timer.elapsed_ms("tts_start", "tts_end"),
        tts_ready_ms=timer.elapsed_ms("tts_start", "tts_end"),
        first_audio_ms=None,
    )


def compute_voice_response_latency_ms(
    *,
    speech_end_monotonic: float | None,
    agent_audio_started_monotonic: float | None,
) -> float | None:
    """Challenge boundary: patient speech end → first agent audio (same clock)."""
    if speech_end_monotonic is None or agent_audio_started_monotonic is None:
        return None
    delta = (agent_audio_started_monotonic - speech_end_monotonic) * 1000.0
    if delta < 0:
        return None
    return delta


def timing_to_metrics(timing: VoiceTurnTiming) -> dict[str, Any]:
    return {
        "stt_ms": timing.stt_ms,
        "tts_ms": timing.tts_ms,
        "tts_ready_ms": timing.tts_ready_ms,
        "first_audio_ms": timing.first_audio_ms,
        "voice_response_latency_ms": timing.voice_response_latency_ms,
        # Challenge boundary (browser playback). Proxy is explicitly named.
        "SERVER_TTS_READY_PROXY_ms": timing.extras.get("SERVER_TTS_READY_PROXY_ms"),
        **{k: v for k, v in timing.extras.items() if k != "SERVER_TTS_READY_PROXY_ms"},
    }
