"""STT providers."""

from __future__ import annotations

from limen.config.settings import ApplicationSettings
from limen.voice.contracts import STTProvider, Transcript


class StubSTTProvider:
    async def transcribe(self, audio: bytes, language: str = "es") -> Transcript:
        return Transcript(
            text="[stub transcript]",
            language=language,
            confidence=1.0,
            latency_ms=1.0,
        )


def build_stt_provider(settings: ApplicationSettings) -> STTProvider:
    if settings.stt_provider.lower().strip() == "stub":
        return StubSTTProvider()
    raise ValueError(f"Unsupported STT_PROVIDER={settings.stt_provider!r}. Use 'stub'.")
