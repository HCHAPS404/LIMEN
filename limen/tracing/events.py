"""Structured trace events for TRAZA — re-export canonical contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from limen.tracing.contracts import (
    TRACE_SCHEMA_VERSION,
    CallMetrics,
    CanonicalTraceEvent,
    CostRecord,
    ErrorTelemetry,
    ProviderUsage,
    RetrievalTelemetry,
    SafetyTracePayload,
    TurnMetrics,
    resolve_event_type,
)


class TraceEvent(BaseModel):
    """Legacy lightweight event — prefer CanonicalTraceEvent."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    stage: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "TRACE_SCHEMA_VERSION",
    "CallMetrics",
    "CanonicalTraceEvent",
    "CostRecord",
    "ErrorTelemetry",
    "ProviderUsage",
    "RetrievalTelemetry",
    "SafetyTracePayload",
    "TraceEvent",
    "TurnMetrics",
    "resolve_event_type",
]
