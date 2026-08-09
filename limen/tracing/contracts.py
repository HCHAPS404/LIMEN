"""Canonical TRAZA event model — schema_versioned, append-friendly."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

TRACE_SCHEMA_VERSION = 1

# Namespaced event types (emit only when the operation actually ran).
TraceEventType = Literal[
    "call.started",
    "turn.received",
    "clinical.extraction.started",
    "clinical.extraction.completed",
    "clinical.state.updated",
    "clinical.uncertainty.completed",
    "retrieval.started",
    "retrieval.dense.completed",
    "retrieval.lexical.completed",
    "retrieval.fusion.completed",
    "retrieval.evidence.selected",
    "safety.evaluation.completed",
    "response.generation.started",
    "response.generation.completed",
    "response.fallback",
    "voice.mic.requested",
    "voice.mic.granted",
    "voice.speech.started",
    "voice.speech.ended",
    "voice.audio.upload.completed",
    "stt.started",
    "stt.completed",
    "turn.processing.started",
    "tts.started",
    "tts.first_audio",
    "tts.completed",
    "voice.playback.started",
    "voice.playback.completed",
    "voice.interrupted",
    "voice.patient_cutoff",
    "voice.false_barge_in",
    "conversation.context.built",
    "conversation.pending_question",
    "conversation.question.answered",
    "conversation.response.interrupted",
    "conversation.intent.pending",
    "conversation.intent.completed",
    "escalation.artifact.persisted",
    "turn.completed",
    "call.completed",
    "knowledge.uploaded",
    "knowledge.processing.started",
    "knowledge.parsed",
    "knowledge.ocr.completed",
    "knowledge.chunked",
    "knowledge.lexical_indexed",
    "knowledge.dense_indexed",
    "knowledge.available",
    "knowledge.deletion.started",
    "knowledge.purged",
    "knowledge.removed",
    "knowledge.failed",
    "provider.error",
    # Legacy UI/API stage aliases kept for reconstruction compatibility.
    "patient_statement",
    "clinical_extraction",
    "uncertainty",
    "retrieval",
    "safety_evaluation",
    "response",
    "escalation",
    "session_end",
]

EventStatus = Literal["ok", "error", "skipped"]

# Map legacy TRAZA stage names → canonical event_type (same row; no duplicate emit).
LEGACY_STAGE_TO_EVENT_TYPE: dict[str, str] = {
    "patient_statement": "turn.received",
    "clinical_extraction": "clinical.extraction.completed",
    "uncertainty": "clinical.uncertainty.completed",
    "retrieval": "retrieval.evidence.selected",
    "safety_evaluation": "safety.evaluation.completed",
    "response": "response.generation.completed",
    "escalation": "safety.evaluation.completed",
    "session_end": "call.completed",
    # Knowledge already uses namespaced stages; normalize a few aliases.
    "knowledge.processing_started": "knowledge.processing.started",
    "knowledge.deletion_started": "knowledge.deletion.started",
    "knowledge.indexed": "knowledge.lexical_indexed",
}


class CanonicalTraceEvent(BaseModel):
    """One append-only TRAZA row (call or knowledge stream)."""

    event_id: str = Field(default_factory=lambda: uuid4().hex)
    event_type: str
    schema_version: int = TRACE_SCHEMA_VERSION
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sequence: int | None = None
    status: EventStatus = "ok"
    duration_ms: float | None = None
    call_id: str | None = None
    turn_id: str | None = None
    document_id: str | None = None
    # Legacy stage string for existing UI / tests (optional alias).
    stage: str | None = None
    label: str | None = None
    detail: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CostRecord(BaseModel):
    estimated_cost_usd: float | None = None
    cost_basis: Literal["measured", "estimated", "not_available", "synthetic"] = "not_available"
    currency: str = "USD"
    notes: str | None = None


class ProviderUsage(BaseModel):
    """Provider-neutral usage — vendor objects must not appear here."""

    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    latency_ms: float | None = None
    generation_ms: float | None = None
    time_to_first_token_ms: float | None = None
    finish_reason: str | None = None
    llm_calls: int | None = None
    embedding_count: int | None = None
    dimensions: int | None = None
    cost: CostRecord = Field(default_factory=CostRecord)


class RetrievalTelemetry(BaseModel):
    query_id: str | None = None
    dense_candidates: int | None = None
    lexical_candidates: int | None = None
    final_candidates: int | None = None
    selected_chunk_ids: list[str] = Field(default_factory=list)
    retrieval_modes: list[str] = Field(default_factory=list)
    dense_ms: float | None = None
    lexical_ms: float | None = None
    fusion_ms: float | None = None
    total_ms: float | None = None


class SafetyTracePayload(BaseModel):
    """Decision facts only — no chain-of-thought."""

    floor_severity: str
    proposed_severity: str
    final_severity: str
    escalate: bool
    reasons: list[str] = Field(default_factory=list)
    downgrade_protected: bool
    policy_version: str | None = None


class ErrorTelemetry(BaseModel):
    stage: str
    error_category: str
    safe_message: str
    provider: str | None = None
    retry_count: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TurnMetrics(BaseModel):
    """Typed turn metrics — unavailable values stay null."""

    total_latency_ms: float | None = None
    clinical_ms: float | None = None
    uncertainty_ms: float | None = None
    retrieval_ms: float | None = None
    safety_ms: float | None = None
    response_generation_ms: float | None = None
    persistence_ms: float | None = None
    dense_ms: float | None = None
    lexical_ms: float | None = None
    fusion_ms: float | None = None
    rag_queries: int = 0
    evidence_candidates: int | None = None
    evidence_selected: int = 0
    llm_calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    cost_basis: Literal["measured", "estimated", "not_available", "synthetic"] = "not_available"


class CallMetrics(BaseModel):
    turn_count: int = 0
    total_duration_ms: float | None = None
    total_llm_calls: int = 0
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    total_rag_queries: int = 0
    total_selected_evidence: int = 0
    estimated_cost_usd: float | None = None
    cost_basis: Literal["measured", "estimated", "not_available", "synthetic"] = "not_available"
    final_risk: str | None = None
    escalated: bool = False
    text_turn_latency_p50_ms: float | None = None
    text_turn_latency_p95_ms: float | None = None
    # Voice speech_end → first_audio is not measurable yet.
    voice_latency_p50_ms: float | None = None
    voice_latency_p95_ms: float | None = None
    voice_latency_status: Literal[
        "not_implemented", "insufficient_samples", "measured"
    ] = "not_implemented"
    voice_latency_sample_count: int = 0
    voice_interruptions: int = 0
    stt_errors: int = 0
    tts_errors: int = 0


def resolve_event_type(*, stage: str, event_type: str | None = None) -> str:
    if event_type:
        return event_type
    return LEGACY_STAGE_TO_EVENT_TYPE.get(stage, stage)
