"""Token / usage counters — preserve in provider adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UsageCounters:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def add(self, prompt: int, completion: int) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
