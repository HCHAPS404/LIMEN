from limen.clinical.uncertainty import ClinicalCertainty


def test_certainty_states_are_explicit() -> None:
    values = {c.value for c in ClinicalCertainty}
    assert values == {
        "KNOWN_NORMAL",
        "KNOWN_ABNORMAL",
        "IMPROVING",
        "UNKNOWN",
        "CONFLICTING",
    }
