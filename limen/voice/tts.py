"""TTS providers."""

from __future__ import annotations

from limen.config.settings import ApplicationSettings
from limen.voice.contracts import AudioResult, TTSProvider


class StubTTSProvider:
    async def synthesize(self, text: str, voice: str) -> AudioResult:
        payload = f"STUB_AUDIO:{voice}:{text}".encode()
        return AudioResult(audio=payload, mime_type="audio/wav", latency_ms=1.0)


def build_tts_provider(settings: ApplicationSettings) -> TTSProvider:
    if settings.tts_provider.lower().strip() == "stub":
        return StubTTSProvider()
    raise ValueError(f"Unsupported TTS_PROVIDER={settings.tts_provider!r}. Use 'stub'.")
