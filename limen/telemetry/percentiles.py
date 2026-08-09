"""Deterministic percentile aggregation for telemetry."""

from __future__ import annotations

import math
from collections.abc import Sequence


def percentile(values: Sequence[float], pct: float) -> float | None:
    """Nearest-rank percentile on a sorted copy (inclusive).

    Method (documented, deterministic):
    1. Empty input → None.
    2. Sort ascending.
    3. rank = ceil(pct/100 * n), clamped to [1, n]; index = rank - 1.

    For a single value, P50 == P95 == that value.
    """
    if not values:
        return None
    if pct < 0 or pct > 100:
        raise ValueError(f"percentile must be in [0, 100], got {pct}")
    ordered = sorted(float(v) for v in values)
    n = len(ordered)
    if pct == 0:
        return ordered[0]
    rank = int(math.ceil((pct / 100.0) * n))
    rank = min(max(rank, 1), n)
    return ordered[rank - 1]


def p50(values: Sequence[float]) -> float | None:
    return percentile(values, 50)


def p95(values: Sequence[float]) -> float | None:
    return percentile(values, 95)
