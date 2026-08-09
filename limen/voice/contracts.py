"""Provider-neutral speech contracts for LIMEN voice runtime."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class Transcript(BaseModel):
    """STT result — patient input for the authoritative text-turn pipeline."""

    text: str
    language: str = "es"
    confidence: float | None = None
    duration_ms: float | None = None
    latency_ms: float = 0.0
    provider: str | None = None
    model: str | None = None
    raw_text: str | None = None
    normalized_text: str | None = None
    usage_metadata: dict[str, Any] = Field(default_factory=dict)


class AudioResult(BaseModel):
    """TTS result — validated patient-facing audio only."""

    audio: bytes = Field(repr=False)
    mime_type: str = "audio/wav"
    sample_rate_hz: int = 16000
    channels: int = 1
    duration_ms: float | None = None
    latency_ms: float = 0.0
    provider: str | None = None
    model: str | None = None
    voice: str | None = None
    usage_metadata: dict[str, Any] = Field(default_factory=dict)


class STTProvider(Protocol):
    provider_name: str

    async def transcribe(self, audio: bytes, language: str = "es") -> Transcript: ...

    async def health(self) -> dict[str, Any]: ...


class TTSProvider(Protocol):
    provider_name: str

    async def synthesize(self, text: str, voice: str) -> AudioResult: ...

    async def health(self) -> dict[str, Any]: ...
