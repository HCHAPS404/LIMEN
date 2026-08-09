"""PHASE 5 LLM benchmark schemas (benchmark-only; not production ClinicalState)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from limen.clinical.uncertainty import ClinicalCertainty

AdvisoryRisk = Literal["GREEN", "YELLOW", "ORANGE", "RED"]


class BenchmarkFinding(BaseModel):
    name: str
    certainty: ClinicalCertainty
    negated: bool = False
    temporal: str | None = None
    severity_qualifier: str | None = None
    notes: str | None = None


class BenchmarkInterpretation(BaseModel):
    """Structured clinical language interpretation for benchmark Task A."""

    findings: list[BenchmarkFinding] = Field(default_factory=list)
    negations: list[str] = Field(default_factory=list)
    symptom_descriptions: list[str] = Field(default_factory=list)
    temporal_information: list[str] = Field(default_factory=list)
    severity_qualifiers: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class BenchmarkAdvisoryRisk(BaseModel):
    """Benchmark-only advisory risk — never enters SafetyDecision."""

    proposed_risk: AdvisoryRisk
    reasons: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "low"
