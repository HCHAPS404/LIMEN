"""WAV PCM helpers — no FFmpeg required for the canonical voice path."""

from __future__ import annotations

import io
import struct
import wave
from typing import Any


CANONICAL_SAMPLE_RATE_HZ = 16_000
CANONICAL_CHANNELS = 1
CANONICAL_SAMPLE_WIDTH = 2  # 16-bit PCM


class AudioFormatError(ValueError):
    """Raised when bytes are not a supported PCM WAV payload."""


def write_pcm16_wav(
    pcm: bytes,
    *,
    sample_rate_hz: int = CANONICAL_SAMPLE_RATE_HZ,
    channels: int = CANONICAL_CHANNELS,
) -> bytes:
    """Wrap raw little-endian PCM16 samples as a WAV container."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(CANONICAL_SAMPLE_WIDTH)
        wf.setframerate(sample_rate_hz)
        wf.writeframes(pcm)
    return buffer.getvalue()


def read_wav_pcm16(data: bytes) -> tuple[bytes, int, int]:
    """Return (pcm_bytes, sample_rate_hz, channels) for PCM16 WAV."""
    try:
        with wave.open(io.BytesIO(data), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
    except wave.Error as exc:
        raise AudioFormatError(f"invalid_wav:{exc}") from exc
    if sample_width != CANONICAL_SAMPLE_WIDTH:
        raise AudioFormatError(f"unsupported_sample_width:{sample_width}")
    if channels not in {1, 2}:
        raise AudioFormatError(f"unsupported_channels:{channels}")
    return frames, int(sample_rate), int(channels)


def wav_duration_ms(data: bytes) -> float | None:
    try:
        pcm, rate, channels = read_wav_pcm16(data)
    except (AudioFormatError, EOFError, OSError):
        return None
    if rate <= 0 or channels <= 0:
        return None
    samples = len(pcm) // (CANONICAL_SAMPLE_WIDTH * channels)
    return (samples / float(rate)) * 1000.0


def pcm16_mono_float32(pcm: bytes, channels: int) -> list[float]:
    """Convert PCM16 (mono or stereo→mono average) to float32 samples in [-1, 1]."""
    if channels not in {1, 2}:
        raise AudioFormatError(f"unsupported_channels:{channels}")
    count = len(pcm) // CANONICAL_SAMPLE_WIDTH
    if count * CANONICAL_SAMPLE_WIDTH != len(pcm):
        raise AudioFormatError("truncated_pcm")
    samples = struct.unpack("<" + "h" * count, pcm)
    if channels == 1:
        return [s / 32768.0 for s in samples]
    out: list[float] = []
    for i in range(0, len(samples), 2):
        left = samples[i]
        right = samples[i + 1] if i + 1 < len(samples) else left
        out.append(((left + right) / 2.0) / 32768.0)
    return out


def resample_linear(samples: list[float], src_rate: int, dst_rate: int) -> list[float]:
    if src_rate == dst_rate or not samples:
        return list(samples)
    if src_rate <= 0 or dst_rate <= 0:
        raise AudioFormatError("invalid_sample_rate")
    duration = len(samples) / float(src_rate)
    dst_len = max(1, int(round(duration * dst_rate)))
    if dst_len == 1:
        return [samples[0]]
    out: list[float] = []
    for i in range(dst_len):
        src_pos = i * (len(samples) - 1) / (dst_len - 1)
        left = int(src_pos)
        right = min(left + 1, len(samples) - 1)
        frac = src_pos - left
        out.append(samples[left] * (1.0 - frac) + samples[right] * frac)
    return out


def wav_to_mono_16k_float32(data: bytes) -> tuple[list[float], dict[str, Any]]:
    """Canonical STT input: mono float32 @ 16 kHz."""
    pcm, rate, channels = read_wav_pcm16(data)
    samples = pcm16_mono_float32(pcm, channels)
    resampled = resample_linear(samples, rate, CANONICAL_SAMPLE_RATE_HZ)
    meta = {
        "source_sample_rate_hz": rate,
        "source_channels": channels,
        "canonical_sample_rate_hz": CANONICAL_SAMPLE_RATE_HZ,
        "sample_count": len(resampled),
        "duration_ms": (len(resampled) / float(CANONICAL_SAMPLE_RATE_HZ)) * 1000.0,
    }
    return resampled, meta


def silence_wav(
    *,
    duration_ms: float = 200.0,
    sample_rate_hz: int = CANONICAL_SAMPLE_RATE_HZ,
) -> bytes:
    n = max(1, int(sample_rate_hz * (duration_ms / 1000.0)))
    return write_pcm16_wav(b"\x00\x00" * n, sample_rate_hz=sample_rate_hz)


def normalize_transcript_text(text: str) -> str:
    """Whitespace-only normalization — never rewrite negations/numbers."""
    return " ".join((text or "").strip().split())
