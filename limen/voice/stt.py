"""STT providers."""

from __future__ import annotations

import os
import threading
import time
from typing import Any

from limen.config.settings import ApplicationSettings
from limen.voice.audio_codec import normalize_transcript_text, wav_duration_ms
from limen.voice.contracts import STTProvider, Transcript

_cache_lock = threading.Lock()
_cached_provider: STTProvider | None = None
_cached_key: str | None = None


class StubSTTProvider:
    provider_name = "stub"

    def __init__(self, model: str = "stub-stt") -> None:
        self.model = model

    async def transcribe(self, audio: bytes, language: str = "es") -> Transcript:
        started = time.perf_counter()
        # Deterministic fixture transcript for any non-empty payload (tests + WS).
        raw = "[stub transcript]" if audio else ""
        normalized = normalize_transcript_text(raw)
        return Transcript(
            text=normalized,
            language=language,
            confidence=1.0 if normalized else None,
            duration_ms=wav_duration_ms(audio),
            latency_ms=(time.perf_counter() - started) * 1000.0,
            provider=self.provider_name,
            model=self.model,
            raw_text=raw,
            normalized_text=normalized,
        )

    async def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "provider": self.provider_name,
            "model": self.model,
            "reachable": True,
            "configured_device": "stub",
            "actual_device": "stub",
            "degraded": False,
            "fallback_reason": None,
        }


def _stt_cache_key(settings: ApplicationSettings) -> str:
    allow = (
        settings.stt_allow_cpu_fallback if "STT_ALLOW_CPU_FALLBACK" in os.environ else None
    )
    return "|".join(
        [
            settings.stt_provider.lower().strip(),
            settings.stt_model or "",
            settings.stt_device or "",
            settings.stt_compute_type or "",
            settings.stt_model_path or "",
            str(allow),
        ]
    )


def reset_stt_provider_for_tests() -> None:
    """Drop process-wide STT singleton (tests only)."""
    global _cached_provider, _cached_key
    with _cache_lock:
        _cached_provider = None
        _cached_key = None


def build_stt_provider(settings: ApplicationSettings) -> STTProvider:
    """Return a process-wide singleton per STT configuration.

    A second Faster-Whisper CUDA load on an already-full GPU OOMs the API
    process (SIGKILL) when starting a call. Lifespan and WebSocket must share
    one provider instance.
    """
    global _cached_provider, _cached_key
    key = _stt_cache_key(settings)
    with _cache_lock:
        if _cached_provider is not None and _cached_key == key:
            return _cached_provider

        provider = settings.stt_provider.lower().strip()
        if provider == "stub":
            built: STTProvider = StubSTTProvider(model=settings.stt_model)
        elif provider in {"faster_whisper", "faster-whisper", "whisper"}:
            from limen.voice.providers.faster_whisper_stt import FasterWhisperSTTProvider

            allow: bool | None = (
                settings.stt_allow_cpu_fallback
                if "STT_ALLOW_CPU_FALLBACK" in os.environ
                else None
            )
            built = FasterWhisperSTTProvider(
                model=settings.stt_model or "Systran/faster-whisper-small",
                device=settings.stt_device,
                compute_type=settings.stt_compute_type,
                download_root=settings.stt_model_path or None,
                allow_cpu_fallback=allow,
            )
        else:
            raise ValueError(
                f"Unsupported STT_PROVIDER={settings.stt_provider!r}. "
                "Use 'stub' or 'faster_whisper'."
            )
        _cached_provider = built
        _cached_key = key
        return built

