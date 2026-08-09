"""Serializable clinical state models (foundation stubs)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from limen.clinical.uncertainty import ClinicalCertainty


class Finding(BaseModel):
    """A single clinical finding with explicit certainty."""

    name: str
    certainty: ClinicalCertainty = ClinicalCertainty.UNKNOWN
    notes: str | None = None


class ClinicalState(BaseModel):
    """Session-scoped clinical state — serializable, provider-neutral."""

    findings: list[Finding] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    summary_notes: str | None = None
