"""Cost accounting — never invent production pricing."""

from __future__ import annotations

from limen.tracing.contracts import CostRecord


def cost_not_available(*, notes: str | None = None) -> CostRecord:
    return CostRecord(
        estimated_cost_usd=None,
        cost_basis="not_available",
        notes=notes,
    )


def cost_from_usage(
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    input_price_per_1k: float | None = None,
    output_price_per_1k: float | None = None,
    local_runtime: bool = False,
) -> CostRecord:
    """Compute cost only when prices and token counts are both known.

    LOCAL providers may report measured API cost 0 when explicitly configured;
    without prices, basis stays ``not_available`` (never fake zero as measured).
    """
    if local_runtime and input_price_per_1k is None and output_price_per_1k is None:
        return CostRecord(
            estimated_cost_usd=0.0,
            cost_basis="measured",
            notes="local_runtime_api_cost_zero",
        )
    if (
        input_tokens is None
        or output_tokens is None
        or input_price_per_1k is None
        or output_price_per_1k is None
    ):
        return cost_not_available(notes="missing_prices_or_tokens")
    if input_price_per_1k < 0 or output_price_per_1k < 0:
        return cost_not_available(notes="invalid_price")
    usd = (input_tokens / 1000.0) * input_price_per_1k + (
        output_tokens / 1000.0
    ) * output_price_per_1k
    return CostRecord(estimated_cost_usd=usd, cost_basis="estimated")


# Backward-compatible helper — prefer cost_from_usage / cost_not_available.
def estimate_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    rate_per_1k: float = 0.0,
) -> float | None:
    """Legacy helper. Returns None when rate is unset (do not treat as $0)."""
    if rate_per_1k <= 0:
        return None
    return ((prompt_tokens + completion_tokens) / 1000.0) * rate_per_1k
