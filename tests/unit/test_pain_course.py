"""Pain severity transition preserves peak and marks IMPROVING."""

from __future__ import annotations

from limen.clinical.extraction import extract_from_utterance
from limen.clinical.uncertainty import ClinicalCertainty
from limen.conversation.context import extract_pain_severity_transition


def test_transition_de_7_a_4() -> None:
    assert extract_pain_severity_transition(
        "creo que el dolor ha bajado de 7 a 4"
    ) == (7, 4)


def test_peak_preserved_and_improving_label() -> None:
    state = extract_from_utterance("Me duele como un siete")
    pain = next(f for f in state.findings if f.name == "pain_severity")
    assert pain.certainty == ClinicalCertainty.KNOWN_ABNORMAL
    assert "pico=7/10" in pain.notes or "actual=7/10" in pain.notes

    state = extract_from_utterance(
        "pues me estoy sintiendo mejor, creo que el dolor ha bajado de 7 a 4",
        state,
    )
    pain2 = next(f for f in state.findings if f.name == "pain_severity")
    assert pain2.certainty == ClinicalCertainty.IMPROVING
    assert "pico=7/10" in pain2.notes
    assert "actual=4/10" in pain2.notes
    assert "mejorando" in pain2.notes
