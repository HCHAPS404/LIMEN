"""Stage timing for challenge-critical latency stages."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class StageTimer:
    marks: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        self.marks[name] = time.perf_counter()

    def elapsed_ms(self, start: str, end: str) -> float | None:
        if start not in self.marks or end not in self.marks:
            return None
        return (self.marks[end] - self.marks[start]) * 1000

    @contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        start_key = f"{stage}_start"
        end_key = f"{stage}_end"
        self.mark(start_key)
        try:
            yield
        finally:
            self.mark(end_key)
