"""Speech provider contracts."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class Transcript(BaseModel):
    text: str
    language: str = "es"
    confidence: float | None = None
    latency_ms: float = 0.0


class AudioResult(BaseModel):
    audio: bytes = Field(repr=False)
    mime_type: str = "audio/wav"
    sample_rate_hz: int = 16000
    latency_ms: float = 0.0


class STTProvider(Protocol):
    async def transcribe(self, audio: bytes, language: str = "es") -> Transcript: ...


class TTSProvider(Protocol):
    async def synthesize(self, text: str, voice: str) -> AudioResult: ...
