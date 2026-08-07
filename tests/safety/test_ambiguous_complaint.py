from limen.safety.decision import Severity
from limen.safety.governor import SafetyGovernor


def test_fever_is_yellow_not_green() -> None:
    gov = SafetyGovernor()
    decision = gov.evaluate_utterance("tengo fiebre desde anoche")
    assert decision.severity == Severity.YELLOW
