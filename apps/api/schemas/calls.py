"""Call transport schemas — never expose ORM/sqlite rows directly."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["GREEN", "YELLOW", "ORANGE", "RED"]
ClinicalCertaintyLiteral = Literal[
    "KNOWN_NORMAL",
    "KNOWN_ABNORMAL",
    "UNKNOWN",
    "CONFLICTING",
]


class CreateCallRequest(BaseModel):
    patient_alias: str = Field(default="Paciente", min_length=1, max_length=80)
    procedure: str | None = Field(default=None, max_length=120)
    postoperative_day: int | None = Field(default=None, ge=0, le=365)


class CallSummaryResponse(BaseModel):
    call_id: str
    patient_alias: str
    procedure: str | None = None
    postoperative_day: int | None = None
    started_at: datetime | str
    duration_seconds: int | None = None
    final_risk: RiskLevel | None = None
    escalated: bool


class FindingPayload(BaseModel):
    """Transport mirror of limen.clinical.state.Finding — certainty stays explicit."""

    name: str
    certainty: ClinicalCertaintyLiteral = "UNKNOWN"
    notes: str | None = None


class ClinicalStatePayload(BaseModel):
    """Transport mirror of limen.clinical.state.ClinicalState."""

    findings: list[FindingPayload] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    summary_notes: str | None = None


class CallDetailResponse(BaseModel):
    call: CallSummaryResponse
    summary: dict[str, Any] | None = None
    clinical_state: ClinicalStatePayload
    metrics: dict[str, Any]
    turns: list[dict[str, Any]]


class TextTurnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class SafetyTurnPayload(BaseModel):
    risk: RiskLevel
    escalate: bool
    reasons: list[str] = Field(default_factory=list)
    policy_version: str


class EvidenceChunkPayload(BaseModel):
    document_id: str
    chunk_id: str
    text: str
    source_name: str
    page: int | None = None
    score: float = 0.0
    version: int = 1
    version_id: str | None = None
    filename: str | None = None
    section: str | None = None
    content_hash: str | None = None
    active: bool = True
    retrieval_modes: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class TextTurnResponse(BaseModel):
    assistant_text: str
    clinical_state: ClinicalStatePayload
    safety: SafetyTurnPayload
    evidence: list[EvidenceChunkPayload] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
