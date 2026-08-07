"""Call session model — provider-neutral."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from limen.clinical.state import ClinicalState
from limen.safety.decision import SafetyDecision


class CallSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    clinical_state: ClinicalState = Field(default_factory=ClinicalState)
    latest_safety: SafetyDecision | None = None
    turn_count: int = 0
