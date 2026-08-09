"""Unit tests for telemetry percentiles, cost, and aggregation."""

from __future__ import annotations

import pytest

from limen.telemetry.aggregates import aggregate_call_metrics
from limen.telemetry.cost import cost_from_usage, cost_not_available, estimate_cost_usd
from limen.telemetry.percentiles import p50, p95, percentile
from limen.tracing.contracts import TurnMetrics, resolve_event_type


def test_percentile_empty_is_none() -> None:
    assert percentile([], 50) is None
    assert p50([]) is None
    assert p95([]) is None


def test_percentile_single_value() -> None:
    assert p50([10.0]) == 10.0
    assert p95([10.0]) == 10.0


def test_percentile_known_dataset() -> None:
    # Nearest-rank: n=20, P50 → rank 10 → 10th value (1-indexed)
    values = [float(i) for i in range(1, 21)]
    assert p50(values) == 10.0
    # P95 → ceil(0.95*20)=19 → 19.0
    assert p95(values) == 19.0


def test_percentile_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        percentile([1.0], 101)


def test_cost_not_available() -> None:
    record = cost_not_available()
    assert record.estimated_cost_usd is None
    assert record.cost_basis == "not_available"


def test_estimate_cost_usd_null_when_unpriced() -> None:
    assert estimate_cost_usd(100, 50, rate_per_1k=0.0) is None


def test_cost_from_usage_requires_prices() -> None:
    missing = cost_from_usage(input_tokens=10, output_tokens=5)
    assert missing.estimated_cost_usd is None
    priced = cost_from_usage(
        input_tokens=1000,
        output_tokens=1000,
        input_price_per_1k=0.001,
        output_price_per_1k=0.002,
    )
    assert priced.estimated_cost_usd == pytest.approx(0.003)
    assert priced.cost_basis == "estimated"


def test_aggregate_null_tokens_stay_null() -> None:
    turns = [
        TurnMetrics(llm_calls=0, input_tokens=None, output_tokens=None, rag_queries=1),
        TurnMetrics(llm_calls=1, input_tokens=10, output_tokens=4, rag_queries=0),
    ]
    agg = aggregate_call_metrics(turns, final_risk="GREEN", escalated=False)
    assert agg.turn_count == 2
    assert agg.total_llm_calls == 1
    assert agg.total_input_tokens == 10
    assert agg.total_output_tokens == 4
    assert agg.total_rag_queries == 1
    assert agg.estimated_cost_usd is None
    assert agg.voice_latency_status == "not_implemented"


def test_aggregate_null_plus_null_tokens() -> None:
    turns = [
        TurnMetrics(llm_calls=0, input_tokens=None, output_tokens=None),
        TurnMetrics(llm_calls=0, input_tokens=None, output_tokens=None),
    ]
    agg = aggregate_call_metrics(turns)
    assert agg.total_input_tokens is None
    assert agg.total_output_tokens is None


def test_resolve_event_type_legacy() -> None:
    assert resolve_event_type(stage="patient_statement") == "turn.received"
    assert resolve_event_type(stage="retrieval") == "retrieval.evidence.selected"
