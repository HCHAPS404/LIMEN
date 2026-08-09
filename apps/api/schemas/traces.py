"""TRAZA transport schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TraceStage = Literal[
    "call.started",
    "patient_statement",
    "clinical_extraction",
    "uncertainty",
    "retrieval",
    "safety_evaluation",
    "response",
    "conversation",
    "voice",
    "escalation",
    "session_end",
    "provider.error",
]

RiskLevel = Literal["GREEN", "YELLOW", "ORANGE", "RED"]


class TraceEventResponse(BaseModel):
    event_id: str
    call_id: str
    sequence: int
    stage: TraceStage | str
    event_type: str | None = None
    schema_version: int = 1
    timestamp: datetime | str
    label: str
    detail: str | None = None
    risk: RiskLevel | None = None
    escalate: bool | None = None
    reasons: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] | None = None
    turn_id: str | None = None
    document_id: str | None = None
    duration_ms: float | None = None
    status: str | None = "ok"
    payload: dict[str, Any] = Field(default_factory=dict)


class CallTraceResponse(BaseModel):
    call_id: str
    events: list[TraceEventResponse]
    final_risk: RiskLevel | None = None
    escalated: bool
    totals: dict[str, Any] | None = None
    schema_version: int = 1
    conversation_debug: dict[str, Any] | None = None
