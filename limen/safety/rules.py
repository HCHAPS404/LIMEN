"""Deterministic safety rules — callable without an LLM."""

from __future__ import annotations

import re

from limen.safety.decision import SafetyDecision, Severity

# Lexical red-flag patterns for foundation smoke tests only.
# Full clinical policy lives in later Safety Governor work / BACKEND.md.
_RED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bno\s+puedo\s+respirar\b", re.IGNORECASE),
    re.compile(r"\bdificultad\s+respiratoria\s+severa\b", re.IGNORECASE),
    re.compile(r"\bdolor\s+de\s+pecho\s+intenso\b", re.IGNORECASE),
    re.compile(r"\bsangrado\s+abundante\b", re.IGNORECASE),
)

_YELLOW_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bfiebre\b", re.IGNORECASE),
    re.compile(r"\bn[aá]useas?\b", re.IGNORECASE),
)


def evaluate_text_rules(text: str) -> SafetyDecision:
    """Rule-based evaluation; never derives decisions from challenge case IDs."""
    reasons: list[str] = []
    severity = Severity.GREEN

    for pattern in _RED_PATTERNS:
        if pattern.search(text):
            severity = max(severity, Severity.RED)
            reasons.append(f"red_pattern:{pattern.pattern}")

    for pattern in _YELLOW_PATTERNS:
        if pattern.search(text):
            severity = max(severity, Severity.YELLOW)
            reasons.append(f"yellow_pattern:{pattern.pattern}")

    if not reasons:
        return SafetyDecision.green()

    return SafetyDecision(
        severity=severity,
        reasons=reasons,
        escalate=severity >= Severity.ORANGE,
    )
