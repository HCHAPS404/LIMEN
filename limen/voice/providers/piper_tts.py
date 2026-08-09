"""Piper TTS adapter — vendor import stays inside this module."""

from __future__ import annotations

import array
import asyncio
import io
import time
import wave
from pathlib import Path
from typing import Any

from limen.voice.audio_codec import write_pcm16_wav
from limen.voice.contracts import AudioResult
from limen.voice.personas import get_persona, list_personas, normalize_persona_id
from limen.voice.speech_text import prepare_speech_text

# Near Piper pack defaults; per-persona knobs override in synthesize().
_LENGTH_SCALE = 1.08
_NOISE_SCALE = 0.667
_NOISE_W_SCALE = 0.80
_SENTENCE_SILENCE_MS = 160.0
_EDGE_FADE_MS = 14.0


def _silence_pcm16(*, sample_rate_hz: int, duration_ms: float) -> bytes:
    n = max(0, int(sample_rate_hz * duration_ms / 1000.0))
    return b"\x00\x00" * n


def _apply_edge_fade(pcm: bytes, *, sample_rate_hz: int, fade_ms: float) -> bytes:
    if not pcm or fade_ms <= 0:
        return pcm
    samples = array.array("h")
    samples.frombytes(pcm)
    fade_n = int(sample_rate_hz * fade_ms / 1000.0)
    if fade_n <= 0 or len(samples) < fade_n * 2:
        return pcm
    for i in range(fade_n):
        gain = i / fade_n
        samples[i] = int(samples[i] * gain)
        samples[-(i + 1)] = int(samples[-(i + 1)] * gain)
    return samples.tobytes()


def _join_pcm_chunks(
    chunks: list[bytes],
    *,
    sample_rate_hz: int,
    sentence_silence_ms: float,
) -> bytes:
    if not chunks:
        return b""
    if len(chunks) == 1:
        return chunks[0]
    silence = _silence_pcm16(sample_rate_hz=sample_rate_hz, duration_ms=sentence_silence_ms)
    out = bytearray(chunks[0])
    for chunk in chunks[1:]:
        out.extend(silence)
        out.extend(chunk)
    return bytes(out)


class PiperTTSProvider:
    provider_name = "piper"

    def __init__(
        self,
        *,
        model_path: str | Path | None = None,
        voice: str = "es_MX-claude-high",
        download_dir: str | Path | None = None,
    ) -> None:
        # Default Piper stem (Elena); synthesize() may switch among installed voices.
        self.voice_name = voice
        self.model_path = Path(model_path) if model_path else None
        self._explicit_download_dir = download_dir is not None
        self.download_dir = Path(download_dir) if download_dir else Path("runtime/models/piper")
        self._voices: dict[str, Any] = {}
        self._sample_rates: dict[str, int] = {}
        self._sample_rate: int = 22050

    def _resolve_request(self, voice: str) -> tuple[str, int | None, str, Any]:
        """Return (piper_stem, speaker_id, label, persona_or_none)."""
        raw = (voice or "").strip() or self.voice_name
        if raw.casefold() in {"elena", "nikolas", "anikka", "alex"}:
            persona = get_persona(raw)
            return persona.piper_voice, persona.speaker_id, persona.id, persona
        folded = raw.casefold()
        for persona in list_personas():
            if persona.display_name.casefold() == folded or persona.piper_voice == raw:
                return persona.piper_voice, persona.speaker_id, persona.id, persona
        return raw, None, raw, None

    def _candidate_paths(self, piper_stem: str) -> list[Path]:
        roots: list[Path] = []
        if self.model_path and self.model_path.is_file():
            # Fixed single-file path only used when stem matches that file.
            return [self.model_path]
        if self.model_path and self.model_path.is_dir():
            roots.append(self.model_path)
        if self.download_dir is not None:
            roots.append(self.download_dir)
        if not self._explicit_download_dir:
            roots.append(Path("runtime/models/piper"))
        seen: set[str] = set()
        candidates: list[Path] = []
        for root in roots:
            key = str(root.resolve()) if root.exists() else str(root)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(root / f"{piper_stem}.onnx")
            candidates.append(root / piper_stem / f"{piper_stem}.onnx")
        return candidates

    def _resolve_model_path(self, piper_stem: str) -> Path:
        if self.model_path and self.model_path.is_file():
            return self.model_path
        candidates = self._candidate_paths(piper_stem)
        for path in candidates:
            if path.is_file():
                return path
        searched = ", ".join(str(p) for p in candidates) or "(none)"
        raise RuntimeError(
            f"Piper voice model not found for {piper_stem!r}. "
            f"Searched: {searched}. "
            "Run `make prepare-voice` or set TTS_MODEL_PATH to the .onnx file. "
            "Use TTS_PROVIDER=stub for CI."
        )

    def _load_stem(self, piper_stem: str) -> Any:
        if piper_stem in self._voices:
            self._sample_rate = self._sample_rates.get(piper_stem, 22050)
            return self._voices[piper_stem]
        try:
            from piper import PiperVoice
        except ImportError as exc:
            raise RuntimeError(
                "piper-tts is not installed. "
                "Install optional voice extras or use TTS_PROVIDER=stub."
            ) from exc
        path = self._resolve_model_path(piper_stem)
        loaded = PiperVoice.load(str(path))
        config = getattr(loaded, "config", None)
        rate = getattr(config, "sample_rate", None) if config is not None else None
        self._voices[piper_stem] = loaded
        self._sample_rates[piper_stem] = int(rate or 22050)
        self._sample_rate = self._sample_rates[piper_stem]
        return loaded

    def _load(self) -> Any:
        # Back-compat for health()/tests that call _load without a stem.
        return self._load_stem(self.voice_name)

    def _synth_config(
        self,
        speaker_id: int | None,
        *,
        length_scale: float | None = None,
        noise_scale: float | None = None,
        noise_w_scale: float | None = None,
    ) -> dict[str, Any]:
        try:
            from piper.config import SynthesisConfig

            kwargs: dict[str, Any] = {
                "length_scale": float(length_scale if length_scale is not None else _LENGTH_SCALE),
                "noise_scale": float(noise_scale if noise_scale is not None else _NOISE_SCALE),
                "noise_w_scale": float(
                    noise_w_scale if noise_w_scale is not None else _NOISE_W_SCALE
                ),
            }
            if speaker_id is not None:
                kwargs["speaker_id"] = int(speaker_id)
            return {"syn_config": SynthesisConfig(**kwargs)}
        except Exception:  # noqa: BLE001 — older piper builds omit SynthesisConfig
            return {}

    def _synthesize_sync(self, text: str, voice: str) -> AudioResult:
        started = time.perf_counter()
        spoken = prepare_speech_text(text)
        piper_stem, speaker_id, label, persona = self._resolve_request(voice)
        # Single-file TTS_MODEL_PATH pins one onnx — ignore stem switches.
        if self.model_path and self.model_path.is_file():
            piper_stem = self.voice_name
            speaker_id = None
            label = self.voice_name
            persona = None
        piper_voice = self._load_stem(piper_stem)
        pcm_chunks: list[bytes] = []
        synth_kwargs = self._synth_config(
            speaker_id,
            length_scale=getattr(persona, "length_scale", None),
            noise_scale=getattr(persona, "noise_scale", None),
            noise_w_scale=getattr(persona, "noise_w_scale", None),
        )

        try:
            for chunk in piper_voice.synthesize(spoken, **synth_kwargs):
                audio_bytes = getattr(chunk, "audio_int16_bytes", None)
                if audio_bytes is None and hasattr(chunk, "audio_int16"):
                    audio_bytes = bytes(chunk.audio_int16)
                if audio_bytes:
                    pcm_chunks.append(audio_bytes)
        except TypeError:
            if synth_kwargs:
                pcm_chunks = []
                try:
                    for chunk in piper_voice.synthesize(spoken):
                        audio_bytes = getattr(chunk, "audio_int16_bytes", None)
                        if audio_bytes is None and hasattr(chunk, "audio_int16"):
                            audio_bytes = bytes(chunk.audio_int16)
                        if audio_bytes:
                            pcm_chunks.append(audio_bytes)
                except TypeError:
                    stream = io.BytesIO()
                    with wave.open(stream, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(self._sample_rate)
                        piper_voice.synthesize(spoken, wf)
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
                        model=piper_stem,
                        voice=label,
                    )
            else:
                stream = io.BytesIO()
                with wave.open(stream, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self._sample_rate)
                    piper_voice.synthesize(spoken, wf)
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
                    model=piper_stem,
                    voice=label,
                )

        pcm = _join_pcm_chunks(
            pcm_chunks,
            sample_rate_hz=self._sample_rate,
            sentence_silence_ms=float(
                getattr(persona, "sentence_silence_ms", None) or _SENTENCE_SILENCE_MS
            ),
        )
        pcm = _apply_edge_fade(pcm, sample_rate_hz=self._sample_rate, fade_ms=_EDGE_FADE_MS)
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
            model=piper_stem,
            voice=label,
        )

    async def synthesize(self, text: str, voice: str) -> AudioResult:
        return await asyncio.to_thread(self._synthesize_sync, text, voice)

    async def health(self) -> dict[str, Any]:
        try:
            path = self._resolve_model_path(self.voice_name)
            await asyncio.to_thread(self._load)
            return {
                "ok": True,
                "provider": self.provider_name,
                "voice": self.voice_name,
                "model_path": str(path),
                "sample_rate_hz": self._sample_rate,
                "reachable": True,
                "personas": [
                    normalize_persona_id(p) for p in ("elena", "nikolas", "anikka", "alex")
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "provider": self.provider_name,
                "voice": self.voice_name,
                "reachable": False,
                "error": f"{type(exc).__name__}:{exc}",
            }
