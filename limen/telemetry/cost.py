"""Cost estimation stubs — never invent production claims."""

from __future__ import annotations


def estimate_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    rate_per_1k: float = 0.0,
) -> float:
    if rate_per_1k <= 0:
        return 0.0
    return ((prompt_tokens + completion_tokens) / 1000.0) * rate_per_1k
