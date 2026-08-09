"""Usage/latency metrics transport."""

from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, HTTPException

from apps.api.dependencies import CurrentAccount, settings_dependency
from apps.api.schemas.metrics import CallMetricsResponse, MetricsSummaryResponse
from limen.persistence.database import get_database
from limen.persistence.repositories.calls import SqliteCallRepository
from limen.persistence.repositories.traces import SqliteTraceRepository
from limen.telemetry.aggregates import aggregate_call_metrics, turn_metrics_from_dict
from limen.telemetry.percentiles import p50, p95

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/calls/{call_id}", response_model=CallMetricsResponse)
async def call_metrics(call_id: str, account: CurrentAccount) -> CallMetricsResponse:
    settings = settings_dependency()
    database = get_database(settings)
    calls = SqliteCallRepository(database)
    row = calls.get_call_row(account.account_id, call_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "call_not_found", "message": "Call not found"},
        )
    events = SqliteTraceRepository(database).list_events(account.account_id, call_id)
    metrics = json.loads(row["metrics_json"] or "{}")
    call_agg = metrics.get("call") if isinstance(metrics, dict) else None
    voice_status = "not_implemented"
    if isinstance(call_agg, dict) and call_agg.get("voice_latency_status"):
        voice_status = str(call_agg["voice_latency_status"])
    elif isinstance(metrics, dict) and metrics.get("voice_latencies_ms"):
        samples = metrics.get("voice_latencies_ms") or []
        if len(samples) >= 3:
            voice_status = "measured"
        elif samples:
            voice_status = "insufficient_samples"
    return CallMetricsResponse(
        call_id=call_id,
        final_risk=row["final_risk"],
        escalated=bool(row["escalated"]),
        metrics=metrics if isinstance(metrics, dict) else {},
        call_aggregation=call_agg if isinstance(call_agg, dict) else None,
        event_count=len(events),
        stages=[event["stage"] for event in events],
        event_types=[event.get("event_type") or event["stage"] for event in events],
        voice_latency_status=voice_status,  # type: ignore[arg-type]
    )


@router.get("/summary", response_model=MetricsSummaryResponse)
async def metrics_summary(account: CurrentAccount) -> MetricsSummaryResponse:
    settings = settings_dependency()
    database = get_database(settings)
    calls_repo = SqliteCallRepository(database)
    calls = calls_repo.list_calls(account.account_id)
    escalated = sum(1 for call in calls if call["escalated"])

    latencies: list[float] = []
    voice_latencies: list[float] = []
    total_llm = 0
    total_rag = 0
    cost_sum: float | None = None
    cost_basis: Literal["measured", "estimated", "not_available", "synthetic"] = "not_available"
    saw_null_cost = False

    for call in calls:
        row = calls_repo.get_call_row(account.account_id, call["call_id"])
        if row is None:
            continue
        blob = json.loads(row["metrics_json"] or "{}")
        if not isinstance(blob, dict):
            continue
        for sample in blob.get("voice_latencies_ms") or []:
            try:
                voice_latencies.append(float(sample))
            except (TypeError, ValueError):
                continue
        turns = blob.get("turns") if isinstance(blob.get("turns"), list) else []
        if not turns:
            continue
        for turn in turns:
            tm = turn_metrics_from_dict(turn)
            if tm.total_latency_ms is not None:
                latencies.append(tm.total_latency_ms)
        agg = aggregate_call_metrics(
            [turn_metrics_from_dict(t) for t in turns],
            final_risk=call.get("final_risk"),
            escalated=bool(call.get("escalated")),
            voice_latencies_ms=blob.get("voice_latencies_ms") or [],
        )
        total_llm += agg.total_llm_calls
        total_rag += agg.total_rag_queries
        if agg.estimated_cost_usd is None:
            saw_null_cost = True
        else:
            cost_sum = (0.0 if cost_sum is None else cost_sum) + agg.estimated_cost_usd
            if cost_basis == "not_available":
                cost_basis = agg.cost_basis

    if saw_null_cost:
        cost_sum = None
        cost_basis = "not_available"

    if not voice_latencies:
        voice_status: Literal["not_implemented", "insufficient_samples", "measured"] = (
            "not_implemented"
        )
        voice_p50 = None
        voice_p95 = None
    elif len(voice_latencies) < 3:
        voice_status = "insufficient_samples"
        voice_p50 = p50(voice_latencies)
        voice_p95 = p95(voice_latencies)
    else:
        voice_status = "measured"
        voice_p50 = p50(voice_latencies)
        voice_p95 = p95(voice_latencies)

    return MetricsSummaryResponse(
        account_id=account.account_id,
        call_count=len(calls),
        escalated_count=escalated,
        text_turn_latency_p50_ms=p50(latencies),
        text_turn_latency_p95_ms=p95(latencies),
        total_llm_calls=total_llm,
        total_rag_queries=total_rag,
        estimated_cost_usd=cost_sum,
        cost_basis=cost_basis,
        voice_latency_p50_ms=voice_p50,
        voice_latency_p95_ms=voice_p95,
        voice_latency_status=voice_status,
        voice_latency_sample_count=len(voice_latencies),
    )
