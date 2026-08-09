"""Deterministic safety rules — callable without an LLM."""

from __future__ import annotations

import re

from limen.clinical.state import ClinicalState
from limen.clinical.uncertainty import ClinicalCertainty
from limen.safety.decision import SafetyDecision, Severity

# Lexical red-flag patterns for foundation smoke tests only.
# Full clinical policy lives in later Safety Governor work / BACKEND.md.
_RED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bno\s+puedo\s+respirar\b", re.IGNORECASE),
    re.compile(r"\bdificultad\s+respiratoria\s+severa\b", re.IGNORECASE),
    re.compile(r"\bdolor\s+de\s+pecho\s+intenso\b", re.IGNORECASE),
    re.compile(r"\bsangrado\s+abundante\b", re.IGNORECASE),
)

_YELLOW_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("fever", re.compile(r"\bfiebre\b", re.IGNORECASE)),
    ("nausea", re.compile(r"\bn[aá]useas?\b", re.IGNORECASE)),
)

# Explicit symptom denial — must not false-trigger the matching yellow token.
# Intentionally narrower than clinical extraction so "no sé si es fiebre" stays yellow.
_EXPLICIT_NEGATIONS: dict[str, re.Pattern[str]] = {
    "fever": re.compile(
        r"\bno\s+(?:tengo|tiene|tenía|present[oa]|estoy\s+con)\s+"
        r"(?:la\s+)?(?:fiebre|febril)\b"
        r"|\bsin\s+(?:efecto\s+(?:de\s+)?)?fiebre\b"
        r"|\bno\s+hay\s+fiebre\b"
        r"|\bno\s+(?:me\s+)?(?:está|esta|estoy|estaba)\s+"
        r"(?:causando|dando|generando|produciendo).{0,48}\bfiebre\b"
        r"|\bno\s+(?:me\s+)?(?:da|dio|causa|causó)\s+"
        r"(?:un\s+)?(?:efecto\s+de\s+)?fiebre\b"
        r"|\bno\s+.{0,40}\befecto\s+de\s+fiebre\b",
        re.IGNORECASE,
    ),
    "nausea": re.compile(
        r"\bno\s+(?:tengo|tiene|tenía|present[oa])\s+"
        r"(?:n[aá]useas?|v[oó]mitos?)\b"
        r"|\bsin\s+n[aá]useas?\b",
        re.IGNORECASE,
    ),
}

_YELLOW_STATE_FINDINGS = frozenset({"fever", "nausea"})


def evaluate_text_rules(text: str) -> SafetyDecision:
    """Rule-based evaluation; never derives decisions from challenge case IDs."""
    reasons: list[str] = []
    severity = Severity.GREEN

    for pattern in _RED_PATTERNS:
        if pattern.search(text):
            severity = max(severity, Severity.RED)
            reasons.append(f"red_pattern:{pattern.pattern}")

    for finding_name, pattern in _YELLOW_PATTERNS:
        if pattern.search(text):
            negation = _EXPLICIT_NEGATIONS.get(finding_name)
            if negation is not None and negation.search(text):
                continue
            severity = max(severity, Severity.YELLOW)
            reasons.append(f"yellow_pattern:{pattern.pattern}")

    if not reasons:
        return SafetyDecision.green()

    return SafetyDecision(
        severity=severity,
        reasons=reasons,
        escalate=severity >= Severity.ORANGE,
    )


def evaluate_state_rules(state: ClinicalState) -> SafetyDecision:
    """Structured findings floor — denied symptoms do not raise YELLOW alone."""
    reasons: list[str] = []
    severity = Severity.GREEN

    for finding in state.findings:
        if finding.name not in _YELLOW_STATE_FINDINGS:
            continue
        if finding.certainty in (
            ClinicalCertainty.KNOWN_ABNORMAL,
            ClinicalCertainty.CONFLICTING,
        ):
            severity = max(severity, Severity.YELLOW)
            reasons.append(f"state_finding:{finding.name}:{finding.certainty.value}")

    if not reasons:
        return SafetyDecision.green("state_no_yellow_findings")

    return SafetyDecision(
        severity=severity,
        reasons=reasons,
        escalate=severity >= Severity.ORANGE,
    )
