"""Typed metrics API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

VoiceLatencyStatus = Literal["not_implemented", "insufficient_samples", "measured"]


class CallMetricsResponse(BaseModel):
    call_id: str
    final_risk: str | None = None
    escalated: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    call_aggregation: dict[str, Any] | None = None
    event_count: int = 0
    stages: list[str] = Field(default_factory=list)
    event_types: list[str] = Field(default_factory=list)
    voice_latency_status: VoiceLatencyStatus = "not_implemented"


class MetricsSummaryResponse(BaseModel):
    account_id: str
    call_count: int
    escalated_count: int
    text_turn_latency_p50_ms: float | None = None
    text_turn_latency_p95_ms: float | None = None
    total_llm_calls: int | None = None
    total_rag_queries: int | None = None
    estimated_cost_usd: float | None = None
    cost_basis: Literal["measured", "estimated", "not_available", "synthetic"] = "not_available"
    voice_latency_p50_ms: float | None = None
    voice_latency_p95_ms: float | None = None
    voice_latency_status: VoiceLatencyStatus = "not_implemented"
    voice_latency_sample_count: int = 0
    note: str = (
        "Aggregates are derived from persisted telemetry only. "
        "Voice latency (speech_end → first_audio) is measured only from real voice samples."
    )
