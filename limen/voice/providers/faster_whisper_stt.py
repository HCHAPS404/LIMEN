"""Faster-Whisper STT adapter — vendor import stays inside this module."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from limen.voice.audio_codec import normalize_transcript_text, wav_to_mono_16k_float32
from limen.voice.contracts import Transcript
from limen.voice.cuda_runtime import ensure_cuda12_library_path
from limen.voice.transcript_repair import STT_INITIAL_PROMPT_ES, repair_transcript_text


class FasterWhisperSTTProvider:
    provider_name = "faster_whisper"

    def __init__(
        self,
        model: str = "Systran/faster-whisper-small",
        *,
        device: str = "auto",
        compute_type: str = "default",
        download_root: str | None = None,
        allow_cpu_fallback: bool | None = None,
    ) -> None:
        self.model_name = model
        self.device = (device or "auto").strip().lower()
        self.compute_type = compute_type
        self.download_root = download_root
        # Explicit cuda must not silently succeed on CPU unless allowed.
        if allow_cpu_fallback is None:
            allow_cpu_fallback = self.device != "cuda"
        self.allow_cpu_fallback = bool(allow_cpu_fallback)
        self._model: Any | None = None
        self._requested_device: str | None = None
        self._actual_device: str | None = None
        self._actual_compute: str | None = None
        self._fallback_reason: str | None = None
        self._cuda_libs: dict[str, Any] | None = None
        self._degraded: bool = False

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import ctranslate2

            return int(ctranslate2.get_cuda_device_count()) > 0
        except Exception:  # noqa: BLE001
            return False

    def _preferred_device_compute(self) -> tuple[str, str]:
        device = self.device
        compute = self.compute_type
        if device == "auto":
            device = "cuda" if self._cuda_available() else "cpu"
        if compute == "default":
            compute = "float16" if device == "cuda" else "int8"
        return device, compute

    def _probe_model(self, model: Any) -> None:
        import numpy as np

        segments, _info = model.transcribe(
            np.zeros(1600, dtype=np.float32),
            language="es",
            beam_size=1,
            vad_filter=False,
        )
        list(segments)

    def _load(self) -> Any:
        if self._model is not None:
            return self._model

        self._cuda_libs = ensure_cuda12_library_path()
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. "
                "Install optional voice extras or use STT_PROVIDER=stub."
            ) from exc

        preferred_device, preferred_compute = self._preferred_device_compute()
        self._requested_device = preferred_device

        attempts: list[tuple[str, str]] = [(preferred_device, preferred_compute)]
        # When cuda+default, also try int8_float16 before any CPU fallback.
        if preferred_device == "cuda" and self.compute_type == "default":
            attempts.append(("cuda", "int8_float16"))
        if preferred_device == "cuda" and self.allow_cpu_fallback:
            attempts.append(("cpu", "int8"))
        elif preferred_device == "auto" and preferred_device != "cpu":
            # auto already resolved; if cuda preferred failed path adds cpu below
            pass

        # Deduplicate attempts
        seen: set[tuple[str, str]] = set()
        ordered: list[tuple[str, str]] = []
        for item in attempts:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)

        last_error: Exception | None = None
        for device, compute in ordered:
            if device == "cpu" and preferred_device == "cuda" and not self.allow_cpu_fallback:
                continue
            kwargs: dict[str, Any] = {
                "device": device,
                "compute_type": compute,
            }
            if self.download_root:
                kwargs["download_root"] = self.download_root
            try:
                model = WhisperModel(self.model_name, **kwargs)
                self._probe_model(model)
                self._model = model
                self._actual_device = device
                self._actual_compute = compute
                if device != preferred_device:
                    self._degraded = True
                    self._fallback_reason = (
                        f"fell_back_from_{preferred_device}_to_{device}:"
                        f"{type(last_error).__name__ if last_error else 'probe_failed'}:"
                        f"{last_error}"
                    )
                elif (
                    preferred_device == "cuda"
                    and compute != preferred_compute
                    and self.compute_type == "default"
                ):
                    # Still on CUDA; alternate compute type is not a device fallback.
                    self._fallback_reason = None
                    self._degraded = False
                return self._model
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        # Explicit cuda without successful cuda init.
        if preferred_device == "cuda" and not self.allow_cpu_fallback:
            raise RuntimeError(
                "faster-whisper CUDA init failed with STT_DEVICE=cuda "
                f"(allow_cpu_fallback=false): {type(last_error).__name__}:{last_error}. "
                "Install nvidia-cublas-cu12 / nvidia-cudnn-cu12 and use "
                "`make prepare-voice` / `scripts/run_voice_api.py`."
            ) from last_error

        raise RuntimeError(
            f"faster-whisper failed to initialize ({preferred_device}/{preferred_compute}): "
            f"{type(last_error).__name__}:{last_error}"
        ) from last_error

    def _placement_metadata(self) -> dict[str, Any]:
        device = self._actual_device or self._preferred_device_compute()[0]
        compute = self._actual_compute or self._preferred_device_compute()[1]
        return {
            "requested_device": self._requested_device or self.device,
            "actual_device": device,
            "configured_device": self.device,
            "compute_type": compute,
            "degraded": self._degraded,
            "fallback_reason": self._fallback_reason,
            "allow_cpu_fallback": self.allow_cpu_fallback,
            "cuda_libs": self._cuda_libs,
        }

    def _transcribe_sync(self, audio: bytes, language: str) -> Transcript:
        started = time.perf_counter()
        samples, meta = wav_to_mono_16k_float32(audio)
        model = self._load()
        try:
            import numpy as np

            array = np.asarray(samples, dtype=np.float32)
        except ImportError:
            array = samples  # type: ignore[assignment]
        segments, info = model.transcribe(
            array,
            language=language or "es",
            beam_size=3,
            best_of=3,
            vad_filter=False,
            condition_on_previous_text=False,
            initial_prompt=STT_INITIAL_PROMPT_ES,
        )
        parts: list[str] = []
        confidences: list[float] = []
        for segment in segments:
            text = str(getattr(segment, "text", "") or "").strip()
            if text:
                parts.append(text)
            prob = getattr(segment, "avg_logprob", None)
            if isinstance(prob, (int, float)):
                confidences.append(max(0.0, min(1.0, 1.0 + float(prob) / 5.0)))
        raw = " ".join(parts).strip()
        normalized = repair_transcript_text(normalize_transcript_text(raw))
        latency = (time.perf_counter() - started) * 1000.0
        confidence = sum(confidences) / len(confidences) if confidences else None
        detected = getattr(info, "language", None) or language
        return Transcript(
            text=normalized,
            language=str(detected),
            confidence=confidence,
            duration_ms=float(meta.get("duration_ms") or 0.0) or None,
            latency_ms=latency,
            provider=self.provider_name,
            model=self.model_name,
            raw_text=raw,
            normalized_text=normalized,
            usage_metadata={
                **self._placement_metadata(),
                "device": self._actual_device,
                "source_audio": meta,
            },
        )

    async def transcribe(self, audio: bytes, language: str = "es") -> Transcript:
        return await asyncio.to_thread(self._transcribe_sync, audio, language)

    async def health(self) -> dict[str, Any]:
        try:
            await asyncio.to_thread(self._load)
            placement = self._placement_metadata()
            ok = True
            # Challenge: STT_DEVICE=cuda must not report healthy success on CPU.
            if self.device == "cuda" and placement.get("actual_device") != "cuda":
                ok = False
            return {
                "ok": ok,
                "provider": self.provider_name,
                "model": self.model_name,
                "reachable": placement.get("actual_device") is not None,
                "degraded": bool(placement.get("degraded")) or not ok,
                "configured_device": placement.get("configured_device"),
                "requested_device": placement.get("requested_device"),
                "actual_device": placement.get("actual_device"),
                "device": placement.get("actual_device"),
                "compute_type": placement.get("compute_type"),
                "fallback_reason": placement.get("fallback_reason"),
                "cuda_libs_ready": bool((placement.get("cuda_libs") or {}).get("ready")),
                "error": (
                    None
                    if ok
                    else (
                        placement.get("fallback_reason")
                        or "STT_DEVICE=cuda but actual_device is not cuda"
                    )
                ),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "provider": self.provider_name,
                "model": self.model_name,
                "reachable": False,
                "degraded": True,
                "configured_device": self.device,
                "requested_device": self.device,
                "actual_device": None,
                "compute_type": None,
                "fallback_reason": f"{type(exc).__name__}:{exc}",
                "error": f"{type(exc).__name__}:{exc}",
            }
