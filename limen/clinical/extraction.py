"""Lexical clinical extraction — no LLM required for the foundation path."""

from __future__ import annotations

import re

from limen.clinical.state import ClinicalState, Finding
from limen.clinical.uncertainty import ClinicalCertainty
from limen.conversation.context import (
    extract_pain_severity_mention,
    extract_pain_severity_transition,
)

_ABNORMAL = ClinicalCertainty.KNOWN_ABNORMAL
_NORMAL = ClinicalCertainty.KNOWN_NORMAL
_PATTERNS: list[tuple[str, re.Pattern[str], ClinicalCertainty]] = [
    ("pain", re.compile(r"\b(dolor|duele|molestia)\b", re.I), _ABNORMAL),
    ("fever", re.compile(r"\b(fiebre|febril|temperatura)\b", re.I), _ABNORMAL),
    ("wound", re.compile(r"\b(herida|cicatriz|punto[s]?)\b", re.I), _ABNORMAL),
    ("bleeding", re.compile(r"\b(sangrado|sangre|hemorragia)\b", re.I), _ABNORMAL),
    ("breathing", re.compile(r"\b(respir|ahogo|falta de aire)\b", re.I), _ABNORMAL),
    ("nausea", re.compile(r"\b(n[aá]usea|v[oó]mito)\b", re.I), _ABNORMAL),
    ("dizziness", re.compile(r"\b(mareo|mareos|v[eé]rtigo)\b", re.I), _ABNORMAL),
    (
        "mood_distress",
        re.compile(
            r"\b(ansios[oa]?|ansiedad|triste(?:za)?|deprimid[oa]|miedo|asustad[oa]|"
            r"llor\w*|desesper\w*|angustia(?:d[oa])?|sin\s+ganas)\b",
            re.I,
        ),
        _ABNORMAL,
    ),
]

# Explicit Spanish negation windows — preserve denied symptoms as KNOWN_NORMAL.
# Fever/nausea patterns avoid "no sé … fiebre" so ambiguity stays non-normal.
_NEGATIONS: list[tuple[str, re.Pattern[str]]] = [
    (
        "fever",
        re.compile(
            r"\bno\s+(?:tengo|tiene|tenía|present[oa]|estoy\s+con)\s+"
            r"(?:la\s+)?(?:fiebre|febril)\b"
            r"|\bsin\s+(?:efecto\s+(?:de\s+)?)?fiebre\b"
            r"|\bno\s+hay\s+fiebre\b"
            # "no me está causando un efecto de fiebre" / "no me da fiebre"
            r"|\bno\s+(?:me\s+)?(?:está|esta|estoy|estaba)\s+"
            r"(?:causando|dando|generando|produciendo).{0,48}\bfiebre\b"
            r"|\bno\s+(?:me\s+)?(?:da|dio|causa|causó)\s+"
            r"(?:un\s+)?(?:efecto\s+de\s+)?fiebre\b"
            r"|\bno\s+.{0,40}\befecto\s+de\s+fiebre\b",
            re.I,
        ),
    ),
    ("pain", re.compile(r"\bno\b.{0,32}\b(dolor|duele)\b|\bsin\s+dolor\b", re.I)),
    ("bleeding", re.compile(r"\bno\b.{0,32}\b(sangrado|sangre)\b|\bsin\s+sangrado\b", re.I)),
    ("breathing", re.compile(r"\bno\b.{0,40}\b(falta de aire|ahogo)\b", re.I)),
    (
        "nausea",
        re.compile(
            r"\bno\s+(?:tengo|tiene|tenía|present[oa])\s+"
            r"(?:n[aá]useas?|v[oó]mitos?)\b"
            r"|\bsin\s+n[aá]useas?\b",
            re.I,
        ),
    ),
]


def empty_state() -> ClinicalState:
    return ClinicalState()


def _upsert_finding(
    state: ClinicalState,
    *,
    name: str,
    certainty: ClinicalCertainty,
    notes: str,
) -> None:
    for finding in state.findings:
        if finding.name != name:
            continue
        if finding.certainty == ClinicalCertainty.CONFLICTING:
            # Preserve conflict until an explicit clinical resolution path exists.
            finding.notes = notes[:160]
            return
        # CONFLICTING if previously abnormal and now denied (or vice versa).
        if finding.certainty != certainty and finding.certainty != ClinicalCertainty.UNKNOWN:
            if {
                finding.certainty,
                certainty,
            } == {ClinicalCertainty.KNOWN_ABNORMAL, ClinicalCertainty.KNOWN_NORMAL}:
                finding.certainty = ClinicalCertainty.CONFLICTING
            else:
                finding.certainty = certainty
        else:
            finding.certainty = certainty
        finding.notes = notes[:160]
        return
    state.findings.append(Finding(name=name, certainty=certainty, notes=notes[:160]))


def extract_from_utterance(text: str, prior: ClinicalState | None = None) -> ClinicalState:
    """Merge lexical findings into prior state. Certainty stays explicit."""
    state = prior.model_copy(deep=True) if prior else ClinicalState()

    # Negations first so "no tengo fiebre" does not also mark fever abnormal
    # from the bare token "fiebre" in the same utterance.
    negated: set[str] = set()
    for name, pattern in _NEGATIONS:
        if pattern.search(text):
            _upsert_finding(state, name=name, certainty=_NORMAL, notes=text)
            negated.add(name)

    for name, pattern, certainty in _PATTERNS:
        if name in negated:
            continue
        if pattern.search(text):
            _upsert_finding(state, name=name, certainty=certainty, notes=text)

    score = extract_pain_severity_mention(text)
    transition = extract_pain_severity_transition(text)
    if score is not None:
        peak = score
        current = score
        if transition is not None:
            peak, current = transition
            if peak < current:
                peak, current = current, peak
        # Preserve historical peak from prior notes when patient reports a drop.
        prior_peak = _peak_from_findings(state)
        if prior_peak is not None:
            peak = max(peak, prior_peak)
        improving = current < peak
        certainty = (
            ClinicalCertainty.IMPROVING if improving else _ABNORMAL
        )
        note = (
            f"pico={peak}/10; actual={current}/10; "
            f"curso={'mejorando' if improving else 'estable'}; {text[:100]}"
        )
        _upsert_finding(state, name="pain", certainty=certainty, notes=note)
        _upsert_finding(
            state,
            name="pain_severity",
            certainty=certainty,
            notes=note,
        )

    # Warmth without claiming fever if fever was negated.
    if re.search(r"\b(caliente|calor|arde)\b", text, re.I) and re.search(
        r"\b(herida|cicatriz)\b", text, re.I
    ):
        _upsert_finding(state, name="wound_heat", certainty=_ABNORMAL, notes=text)

    return state


def _peak_from_findings(state: ClinicalState) -> int | None:
    import re

    for finding in state.findings:
        if finding.name not in {"pain", "pain_severity"}:
            continue
        notes = finding.notes or ""
        for pattern in (
            r"pico=(\d+)/10",
            r"actual=(\d+)/10",
            r"severity=(\d+)/10",
            r"intensidad=(\d+)/10",
        ):
            m = re.search(pattern, notes)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    continue
    return None
