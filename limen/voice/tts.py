"""TTS providers."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from limen.config.settings import ApplicationSettings
from limen.voice.audio_codec import silence_wav, wav_duration_ms
from limen.voice.contracts import AudioResult, TTSProvider

_cache_lock = threading.Lock()
_cached_provider: TTSProvider | None = None
_cached_key: str | None = None


class StubTTSProvider:
    """Produces a short valid silent WAV so browser playback can exercise the path."""

    provider_name = "stub"

    def __init__(self, model: str = "stub-tts", voice: str = "default") -> None:
        self.model = model
        self.default_voice = voice

    async def synthesize(self, text: str, voice: str) -> AudioResult:
        started = time.perf_counter()
        # Duration scales slightly with text length but stays short.
        duration_ms = min(1200.0, 180.0 + 12.0 * max(1, len(text.split())))
        audio = silence_wav(duration_ms=duration_ms)
        return AudioResult(
            audio=audio,
            mime_type="audio/wav",
            sample_rate_hz=16000,
            channels=1,
            duration_ms=wav_duration_ms(audio),
            latency_ms=(time.perf_counter() - started) * 1000.0,
            provider=self.provider_name,
            model=self.model,
            voice=voice or self.default_voice,
            usage_metadata={"stub": True, "text_chars": len(text)},
        )

    async def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "provider": self.provider_name,
            "model": self.model,
            "voice": self.default_voice,
            "reachable": True,
        }


def _tts_cache_key(settings: ApplicationSettings) -> str:
    return "|".join(
        [
            settings.tts_provider.lower().strip(),
            settings.tts_model or "",
            settings.tts_voice or "",
            settings.tts_model_path or "",
        ]
    )


def reset_tts_provider_for_tests() -> None:
    """Drop process-wide TTS singleton (tests only)."""
    global _cached_provider, _cached_key
    with _cache_lock:
        _cached_provider = None
        _cached_key = None


def build_tts_provider(settings: ApplicationSettings) -> TTSProvider:
    """Return a process-wide singleton per TTS configuration."""
    global _cached_provider, _cached_key
    key = _tts_cache_key(settings)
    with _cache_lock:
        if _cached_provider is not None and _cached_key == key:
            return _cached_provider

        provider = settings.tts_provider.lower().strip()
        if provider == "stub":
            built: TTSProvider = StubTTSProvider(
                model=settings.tts_model, voice=settings.tts_voice
            )
        elif provider == "piper":
            from limen.voice.providers.piper_tts import PiperTTSProvider

            raw_path = (settings.tts_model_path or "").strip()
            model_file: str | None = None
            download_dir: str | None = None
            if raw_path.endswith(".onnx"):
                model_file = raw_path
                download_dir = str(Path(raw_path).parent)
            elif raw_path:
                download_dir = raw_path
            built = PiperTTSProvider(
                model_path=model_file,
                voice=settings.tts_voice or "es_MX-claude-high",
                download_dir=download_dir,
            )
        else:
            raise ValueError(
                f"Unsupported TTS_PROVIDER={settings.tts_provider!r}. "
                "Use 'stub' or 'piper'."
            )
        _cached_provider = built
        _cached_key = key
        return built

