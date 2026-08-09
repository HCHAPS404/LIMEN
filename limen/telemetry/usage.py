"""Provider-neutral usage counters and records."""

from __future__ import annotations

from dataclasses import dataclass, field

from limen.telemetry.cost import cost_not_available
from limen.tracing.contracts import CostRecord, ProviderUsage


@dataclass
class UsageCounters:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_calls: int = 0

    def add(self, prompt: int, completion: int, *, calls: int = 1) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.llm_calls += calls


@dataclass
class UsageAccumulator:
    """Null-safe token aggregation across turns."""

    llm_calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    rag_queries: int = 0
    selected_evidence: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    cost: CostRecord = field(default_factory=cost_not_available)

    def add_turn(
        self,
        *,
        llm_calls: int,
        input_tokens: int | None,
        output_tokens: int | None,
        rag_queries: int,
        evidence_selected: int,
        latency_ms: float | None,
        cost: CostRecord | None = None,
    ) -> None:
        self.llm_calls += llm_calls
        self.rag_queries += rag_queries
        self.selected_evidence += evidence_selected
        if latency_ms is not None:
            self.latencies_ms.append(float(latency_ms))
        self.input_tokens = _sum_nullable(self.input_tokens, input_tokens)
        self.output_tokens = _sum_nullable(self.output_tokens, output_tokens)
        if cost is not None:
            self.cost = _merge_cost(self.cost, cost)


def llm_usage(
    *,
    provider: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    latency_ms: float | None = None,
    cached_tokens: int | None = None,
    cost: CostRecord | None = None,
) -> ProviderUsage:
    return ProviderUsage(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        latency_ms=latency_ms,
        cost=cost or cost_not_available(),
    )


def embedding_usage(
    *,
    provider: str,
    model: str,
    embedding_count: int,
    dimensions: int,
    latency_ms: float | None = None,
) -> ProviderUsage:
    return ProviderUsage(
        provider=provider,
        model=model,
        embedding_count=embedding_count,
        dimensions=dimensions,
        latency_ms=latency_ms,
        cost=cost_not_available(notes="embedding_cost_not_configured"),
    )


def _sum_nullable(current: int | None, addition: int | None) -> int | None:
    """Sum tokens only when both sides are known; never coerce null→0."""
    if addition is None:
        return current
    if current is None:
        return addition
    return current + addition


def _merge_cost(current: CostRecord, incoming: CostRecord) -> CostRecord:
    if incoming.cost_basis == "not_available" and incoming.estimated_cost_usd is None:
        if current.estimated_cost_usd is None:
            return current
        return current
    if incoming.estimated_cost_usd is None:
        return CostRecord(estimated_cost_usd=None, cost_basis="not_available")
    if current.estimated_cost_usd is None and current.cost_basis == "not_available":
        return incoming
    if current.estimated_cost_usd is None:
        return CostRecord(estimated_cost_usd=None, cost_basis="not_available")
    return CostRecord(
        estimated_cost_usd=current.estimated_cost_usd + incoming.estimated_cost_usd,
        cost_basis=incoming.cost_basis
        if incoming.cost_basis == current.cost_basis
        else "estimated",
    )
