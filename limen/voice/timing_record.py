"""Per-turn voice timing records with monotonic invariants."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class VoiceTurnTimingRecord:
    """One authoritative timing record per voice turn (same clock family)."""

    sample_id: str
    turn_id: str
    speech_end: float | None = None
    stt_start: float | None = None
    stt_end: float | None = None
    turn_processing_start: float | None = None
    turn_processing_end: float | None = None
    llm_start: float | None = None
    llm_end: float | None = None
    tts_start: float | None = None
    tts_ready: float | None = None
    audio_received_browser: float | None = None
    audio_playback_start: float | None = None
    valid: bool = True
    invalid_reasons: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    def duration_ms(self, start: float | None, end: float | None) -> float | None:
        if start is None or end is None:
            return None
        return (end - start) * 1000.0

    @property
    def stt_ms(self) -> float | None:
        return self.duration_ms(self.stt_start, self.stt_end)

    @property
    def turn_processing_ms(self) -> float | None:
        return self.duration_ms(self.turn_processing_start, self.turn_processing_end)

    @property
    def llm_ms(self) -> float | None:
        return self.duration_ms(self.llm_start, self.llm_end)

    @property
    def tts_ms(self) -> float | None:
        return self.duration_ms(self.tts_start, self.tts_ready)

    @property
    def transport_playback_startup_ms(self) -> float | None:
        # Browser: audio bytes received → first audible playback.
        return self.duration_ms(self.audio_received_browser, self.audio_playback_start)

    @property
    def server_tts_ready_proxy_ms(self) -> float | None:
        """SERVER_TTS_READY_PROXY — not challenge_voice_latency."""
        return self.duration_ms(self.speech_end, self.tts_ready)

    @property
    def challenge_voice_e2e_ms(self) -> float | None:
        """Official boundary: patient speech_end → browser playback start."""
        return self.duration_ms(self.speech_end, self.audio_playback_start)

    def validate_invariants(self) -> bool:
        reasons: list[str] = []

        def _order(a_name: str, a: float | None, b_name: str, b: float | None) -> None:
            if a is None or b is None:
                return
            if a > b:
                reasons.append(f"{a_name}>{b_name}")

        _order("speech_end", self.speech_end, "stt_start", self.stt_start)
        _order("stt_start", self.stt_start, "stt_end", self.stt_end)
        _order("stt_end", self.stt_end, "turn_processing_start", self.turn_processing_start)
        _order(
            "turn_processing_start",
            self.turn_processing_start,
            "turn_processing_end",
            self.turn_processing_end,
        )
        if self.llm_start is not None and self.llm_end is not None:
            _order("llm_start", self.llm_start, "llm_end", self.llm_end)
        _order("tts_start", self.tts_start, "tts_ready", self.tts_ready)
        # tts_ready is server perf_counter; audio_playback_start is browser
        # performance.now(). Do not order those marks against each other.
        _order(
            "audio_received_browser",
            self.audio_received_browser,
            "audio_playback_start",
            self.audio_playback_start,
        )

        e2e = self.challenge_voice_e2e_ms
        stt = self.stt_ms
        # Only when STT lies entirely inside the official E2E boundary.
        if (
            e2e is not None
            and stt is not None
            and self.speech_end is not None
            and self.stt_start is not None
            and self.stt_end is not None
            and self.audio_playback_start is not None
            and self.speech_end <= self.stt_start
            and self.stt_end <= self.audio_playback_start
            and e2e + 1e-6 < stt
        ):
            reasons.append("challenge_e2e_ms<stt_ms")

        proxy = self.server_tts_ready_proxy_ms
        if (
            proxy is not None
            and stt is not None
            and self.speech_end is not None
            and self.stt_start is not None
            and self.stt_end is not None
            and self.tts_ready is not None
            and self.speech_end <= self.stt_start
            and self.stt_end <= self.tts_ready
            and proxy + 1e-6 < stt
        ):
            reasons.append("SERVER_TTS_READY_PROXY<stt_ms")

        self.invalid_reasons = reasons
        self.valid = not reasons
        return self.valid

    def to_metrics(self) -> dict[str, Any]:
        self.validate_invariants()
        return {
            "sample_id": self.sample_id,
            "turn_id": self.turn_id,
            "valid": self.valid,
            "invalid_reasons": list(self.invalid_reasons),
            "stt_ms": self.stt_ms,
            "turn_processing_ms": self.turn_processing_ms,
            "llm_ms": self.llm_ms,
            "tts_ms": self.tts_ms,
            "transport_playback_startup_ms": self.transport_playback_startup_ms,
            "SERVER_TTS_READY_PROXY_ms": self.server_tts_ready_proxy_ms,
            "challenge_voice_e2e_ms": self.challenge_voice_e2e_ms,
            "marks": {
                "speech_end": self.speech_end,
                "stt_start": self.stt_start,
                "stt_end": self.stt_end,
                "turn_processing_start": self.turn_processing_start,
                "turn_processing_end": self.turn_processing_end,
                "llm_start": self.llm_start,
                "llm_end": self.llm_end,
                "tts_start": self.tts_start,
                "tts_ready": self.tts_ready,
                "audio_received_browser": self.audio_received_browser,
                "audio_playback_start": self.audio_playback_start,
            },
            **self.extras,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
