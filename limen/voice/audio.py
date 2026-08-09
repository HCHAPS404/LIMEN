"""WAV PCM helpers re-export surface for limen.voice.audio."""

from __future__ import annotations

from limen.voice.audio_codec import (
    CANONICAL_CHANNELS,
    CANONICAL_SAMPLE_RATE_HZ,
    AudioFormatError,
    normalize_transcript_text,
    read_wav_pcm16,
    silence_wav,
    wav_duration_ms,
    wav_to_mono_16k_float32,
    write_pcm16_wav,
)

__all__ = [
    "CANONICAL_CHANNELS",
    "CANONICAL_SAMPLE_RATE_HZ",
    "AudioFormatError",
    "normalize_transcript_text",
    "read_wav_pcm16",
    "silence_wav",
    "wav_duration_ms",
    "wav_to_mono_16k_float32",
    "write_pcm16_wav",
]
