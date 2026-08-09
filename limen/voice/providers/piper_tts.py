"""Piper TTS adapter — vendor import stays inside this module."""

from __future__ import annotations

import asyncio
import io
import time
import wave
from pathlib import Path
from typing import Any

from limen.voice.audio_codec import write_pcm16_wav
from limen.voice.contracts import AudioResult


class PiperTTSProvider:
    provider_name = "piper"

    def __init__(
        self,
        *,
        model_path: str | Path | None = None,
        voice: str = "es_MX-claude-high",
        download_dir: str | Path | None = None,
    ) -> None:
        self.voice_name = voice
        self.model_path = Path(model_path) if model_path else None
        self._explicit_download_dir = download_dir is not None
        self.download_dir = Path(download_dir) if download_dir else Path("runtime/models/piper")
        self._voice: Any | None = None
        self._sample_rate: int = 22050

    def _resolve_model_path(self) -> Path:
        if self.model_path and self.model_path.is_file():
            return self.model_path
        # TTS_MODEL_PATH may be a directory (download root) or an .onnx file.
        roots: list[Path] = []
        if self.model_path and self.model_path.is_dir():
            roots.append(self.model_path)
        if self.download_dir is not None:
            roots.append(self.download_dir)
        if not self._explicit_download_dir:
            roots.append(Path("runtime/models/piper"))
        # Deduplicate while preserving order.
        seen: set[str] = set()
        candidates: list[Path] = []
        for root in roots:
            key = str(root.resolve()) if root.exists() else str(root)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(root / f"{self.voice_name}.onnx")
            candidates.append(root / self.voice_name / f"{self.voice_name}.onnx")
        for path in candidates:
            if path.is_file():
                return path
        searched = ", ".join(str(p) for p in candidates) or "(none)"
        raise RuntimeError(
            f"Piper voice model not found for {self.voice_name!r}. "
            f"Searched: {searched}. "
            "Run `make prepare-voice` or set TTS_MODEL_PATH to the .onnx file. "
            "Use TTS_PROVIDER=stub for CI."
        )

    def _load(self) -> Any:
        if self._voice is not None:
            return self._voice
        try:
            from piper import PiperVoice
        except ImportError as exc:
            raise RuntimeError(
                "piper-tts is not installed. "
                "Install optional voice extras or use TTS_PROVIDER=stub."
            ) from exc
        path = self._resolve_model_path()
        self._voice = PiperVoice.load(str(path))
        config = getattr(self._voice, "config", None)
        rate = getattr(config, "sample_rate", None) if config is not None else None
        self._sample_rate = int(rate or 22050)
        return self._voice

    def _synthesize_sync(self, text: str, voice: str) -> AudioResult:
        started = time.perf_counter()
        if voice and voice != self.voice_name and not self.model_path:
            # Allow override voice name when path not fixed.
            self.voice_name = voice
            self._voice = None
        piper_voice = self._load()
        pcm_chunks: list[bytes] = []
        # piper API variants: synthesize returns iterator of AudioChunk with .audio_int16_bytes
        try:
            for chunk in piper_voice.synthesize(text):
                audio_bytes = getattr(chunk, "audio_int16_bytes", None)
                if audio_bytes is None and hasattr(chunk, "audio_int16"):
                    audio_bytes = bytes(chunk.audio_int16)
                if audio_bytes:
                    pcm_chunks.append(audio_bytes)
        except TypeError:
            # Older synthesize_stream / stream API
            stream = io.BytesIO()
            with wave.open(stream, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self._sample_rate)
                piper_voice.synthesize(text, wf)
            wav_bytes = stream.getvalue()
            latency = (time.perf_counter() - started) * 1000.0
            return AudioResult(
                audio=wav_bytes,
                mime_type="audio/wav",
                sample_rate_hz=self._sample_rate,
                channels=1,
                duration_ms=None,
                latency_ms=latency,
                provider=self.provider_name,
                model=str(self.model_path or self.voice_name),
                voice=self.voice_name,
            )

        pcm = b"".join(pcm_chunks)
        wav_bytes = write_pcm16_wav(pcm, sample_rate_hz=self._sample_rate, channels=1)
        latency = (time.perf_counter() - started) * 1000.0
        duration_ms = (len(pcm) / 2 / float(self._sample_rate)) * 1000.0 if pcm else None
        return AudioResult(
            audio=wav_bytes,
            mime_type="audio/wav",
            sample_rate_hz=self._sample_rate,
            channels=1,
            duration_ms=duration_ms,
            latency_ms=latency,
            provider=self.provider_name,
            model=str(self.model_path or self.voice_name),
            voice=self.voice_name,
        )

    async def synthesize(self, text: str, voice: str) -> AudioResult:
        return await asyncio.to_thread(self._synthesize_sync, text, voice)

    async def health(self) -> dict[str, Any]:
        try:
            path = self._resolve_model_path()
            await asyncio.to_thread(self._load)
            return {
                "ok": True,
                "provider": self.provider_name,
                "voice": self.voice_name,
                "model_path": str(path),
                "sample_rate_hz": self._sample_rate,
                "reachable": True,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "provider": self.provider_name,
                "voice": self.voice_name,
                "reachable": False,
                "error": f"{type(exc).__name__}:{exc}",
            }
