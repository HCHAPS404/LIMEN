"""Call-level telemetry aggregation from turn metrics / TRAZA events."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from limen.telemetry.percentiles import p50, p95
from limen.telemetry.usage import UsageAccumulator
from limen.tracing.contracts import CallMetrics, CostRecord, TurnMetrics


def turn_metrics_from_dict(raw: dict[str, Any]) -> TurnMetrics:
    basis = raw.get("cost_basis") or "not_available"
    if basis not in {"measured", "estimated", "not_available", "synthetic"}:
        basis = "not_available"
    return TurnMetrics(
        total_latency_ms=_float_or_none(raw.get("latency_ms") or raw.get("total_latency_ms")),
        clinical_ms=_float_or_none(raw.get("clinical_ms")),
        uncertainty_ms=_float_or_none(raw.get("uncertainty_ms")),
        retrieval_ms=_float_or_none(raw.get("retrieval_ms")),
        safety_ms=_float_or_none(raw.get("safety_ms")),
        response_generation_ms=_float_or_none(raw.get("response_generation_ms")),
        persistence_ms=_float_or_none(raw.get("persistence_ms")),
        dense_ms=_float_or_none(raw.get("dense_ms")),
        lexical_ms=_float_or_none(raw.get("lexical_ms")),
        fusion_ms=_float_or_none(raw.get("fusion_ms")),
        rag_queries=int(raw.get("rag_queries") or 0),
        evidence_candidates=_int_or_none(raw.get("evidence_candidates")),
        evidence_selected=int(raw.get("evidence_selected") or raw.get("final_evidence_count") or 0),
        llm_calls=int(raw.get("llm_calls") or 0),
        input_tokens=_int_or_none(raw.get("input_tokens")),
        output_tokens=_int_or_none(raw.get("output_tokens")),
        estimated_cost_usd=_float_or_none(raw.get("estimated_cost_usd")),
        cost_basis=basis,  # type: ignore[arg-type]
    )


def aggregate_call_metrics(
    turns: Sequence[TurnMetrics | dict[str, Any]],
    *,
    final_risk: str | None = None,
    escalated: bool = False,
    voice_latencies_ms: Sequence[float] | None = None,
    voice_interruptions: int = 0,
    stt_errors: int = 0,
    tts_errors: int = 0,
) -> CallMetrics:
    acc = UsageAccumulator()
    for item in turns:
        turn = item if isinstance(item, TurnMetrics) else turn_metrics_from_dict(item)
        acc.add_turn(
            llm_calls=turn.llm_calls,
            input_tokens=turn.input_tokens,
            output_tokens=turn.output_tokens,
            rag_queries=turn.rag_queries,
            evidence_selected=turn.evidence_selected,
            latency_ms=turn.total_latency_ms,
            cost=CostRecord(
                estimated_cost_usd=turn.estimated_cost_usd,
                cost_basis=turn.cost_basis,
            ),
        )
    total_duration = sum(acc.latencies_ms) if acc.latencies_ms else None
    voice_samples = [float(v) for v in (voice_latencies_ms or []) if v is not None]
    if not voice_samples:
        voice_status: str = "not_implemented"
        voice_p50 = None
        voice_p95 = None
    elif len(voice_samples) < 3:
        voice_status = "insufficient_samples"
        voice_p50 = p50(voice_samples)
        voice_p95 = p95(voice_samples)
    else:
        voice_status = "measured"
        voice_p50 = p50(voice_samples)
        voice_p95 = p95(voice_samples)
    return CallMetrics(
        turn_count=len(turns),
        total_duration_ms=total_duration,
        total_llm_calls=acc.llm_calls,
        total_input_tokens=acc.input_tokens,
        total_output_tokens=acc.output_tokens,
        total_rag_queries=acc.rag_queries,
        total_selected_evidence=acc.selected_evidence,
        estimated_cost_usd=acc.cost.estimated_cost_usd,
        cost_basis=acc.cost.cost_basis,
        final_risk=final_risk,
        escalated=escalated,
        text_turn_latency_p50_ms=p50(acc.latencies_ms),
        text_turn_latency_p95_ms=p95(acc.latencies_ms),
        voice_latency_p50_ms=voice_p50,
        voice_latency_p95_ms=voice_p95,
        voice_latency_status=voice_status,  # type: ignore[arg-type]
        voice_latency_sample_count=len(voice_samples),
        voice_interruptions=voice_interruptions,
        stt_errors=stt_errors,
        tts_errors=tts_errors,
    )


def aggregate_from_trace_events(events: list[dict[str, Any]]) -> CallMetrics:
    """Build call metrics from persisted TRAZA events (response-stage metrics)."""
    turns: list[dict[str, Any]] = []
    final_risk: str | None = None
    escalated = False
    for event in events:
        stage = event.get("stage") or event.get("event_type")
        if event.get("risk"):
            final_risk = event["risk"]
        if event.get("escalate"):
            escalated = True
        metrics = event.get("metrics") or {}
        if stage in {"response", "response.generation.completed"} and metrics:
            turns.append(metrics)
        payload = event.get("payload") or {}
        if isinstance(payload, dict) and payload.get("turn_metrics"):
            turns.append(payload["turn_metrics"])
    # Deduplicate if both metrics and payload carried the same turn.
    if len(turns) >= 2 and turns[-1] == turns[-2]:
        turns = turns[:-1]
    return aggregate_call_metrics(turns, final_risk=final_risk, escalated=escalated)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
