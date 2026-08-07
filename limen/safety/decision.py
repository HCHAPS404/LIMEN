"""Safety decision types — severity is monotonic."""

from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel, Field


class Severity(IntEnum):
    """Higher numeric value always wins (monotonic escalation)."""

    GREEN = 0
    YELLOW = 1
    ORANGE = 2
    RED = 3


class SafetyDecision(BaseModel):
    severity: Severity
    reasons: list[str] = Field(default_factory=list)
    escalate: bool = False
    policy_version: str = "foundation-0.1"

    @classmethod
    def green(cls, reason: str = "no_rule_triggered") -> SafetyDecision:
        return cls(severity=Severity.GREEN, reasons=[reason], escalate=False)
