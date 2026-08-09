from limen.clinical.state import ClinicalState, Finding
from limen.clinical.uncertainty import ClinicalCertainty
from limen.clinical.uncertainty_analysis import analyze_uncertainty, apply_uncertainty


def test_unknown_and_conflicting_are_listed_explicitly() -> None:
    state = ClinicalState(
        findings=[
            Finding(name="pain", certainty=ClinicalCertainty.UNKNOWN),
            Finding(name="wound", certainty=ClinicalCertainty.CONFLICTING),
            Finding(name="fever", certainty=ClinicalCertainty.KNOWN_ABNORMAL),
        ]
    )
    report = analyze_uncertainty(state)
    assert "pain" in report.unknown
    assert "wound" in report.conflicting
    assert report.should_retrieve is True
    assert any("dolor" in q.lower() or "pain" in q.lower() for q in report.unresolved)


def test_known_normal_alone_does_not_force_retrieval() -> None:
    state = ClinicalState(
        findings=[Finding(name="pain", certainty=ClinicalCertainty.KNOWN_NORMAL)],
        open_questions=[],
    )
    report = analyze_uncertainty(state)
    assert report.unknown == []
    assert report.conflicting == []
    assert report.should_retrieve is False


def test_apply_uncertainty_preserves_finding_certainty() -> None:
    state = ClinicalState(
        findings=[Finding(name="fever", certainty=ClinicalCertainty.KNOWN_ABNORMAL)],
    )
    report = analyze_uncertainty(state)
    updated = apply_uncertainty(state, report)
    assert updated.findings[0].certainty == ClinicalCertainty.KNOWN_ABNORMAL
    assert updated.open_questions == report.unresolved
