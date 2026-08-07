"""Escalation helpers."""

from limen.safety.decision import SafetyDecision, Severity


def should_escalate(decision: SafetyDecision) -> bool:
    return decision.escalate or decision.severity >= Severity.ORANGE
