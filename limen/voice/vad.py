"""Minimal backend VAD helpers for tests — clinical domain does not use this."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EndpointDecision:
    is_speech: bool
    should_close_utterance: bool
    reason: str


@dataclass
class EndpointConfig:
    speech_threshold: float = 0.045
    silence_threshold: float = 0.02
    min_speech_frames: int = 3
    silence_hangover_frames: int = 12
    max_utterance_frames: int = 500  # ~30s at 60ms/frame
    min_utterance_frames: int = 5


class FrameEndpointer:
    """Frame-level endpointing with min/max utterance guards."""

    def __init__(self, config: EndpointConfig | None = None) -> None:
        self.config = config or EndpointConfig()
        self._in_speech = False
        self._speech_run = 0
        self._silence_run = 0
        self._utterance_frames = 0

    def push(self, level: float) -> EndpointDecision:
        cfg = self.config
        if level >= cfg.speech_threshold:
            self._speech_run += 1
            self._silence_run = 0
        elif level <= cfg.silence_threshold:
            self._silence_run += 1
            self._speech_run = 0

        if not self._in_speech and self._speech_run >= cfg.min_speech_frames:
            self._in_speech = True
            self._utterance_frames = 0
            self._silence_run = 0

        if self._in_speech:
            self._utterance_frames += 1
            if self._utterance_frames >= cfg.max_utterance_frames:
                self._in_speech = False
                return EndpointDecision(True, True, "max_utterance")
            if (
                self._silence_run >= cfg.silence_hangover_frames
                and self._utterance_frames >= cfg.min_utterance_frames
            ):
                self._in_speech = False
                return EndpointDecision(False, True, "silence_hangover")
            if (
                self._silence_run >= cfg.silence_hangover_frames
                and self._utterance_frames < cfg.min_utterance_frames
            ):
                # Too short — treat as false trigger, do not close as clinical utterance.
                self._in_speech = False
                return EndpointDecision(False, False, "false_trigger")
            return EndpointDecision(True, False, "speech")

        return EndpointDecision(False, False, "silence")

    def reset(self) -> None:
        self._in_speech = False
        self._speech_run = 0
        self._silence_run = 0
        self._utterance_frames = 0
