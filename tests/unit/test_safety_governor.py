from limen.safety.decision import Severity
from limen.safety.governor import SafetyGovernor


def test_governor_detects_red_flag_without_llm() -> None:
    gov = SafetyGovernor()
    decision = gov.evaluate_utterance("No puedo respirar desde esta mañana")
    assert decision.severity == Severity.RED
    assert decision.escalate is True


def test_severity_is_monotonic() -> None:
    gov = SafetyGovernor()
    weak = gov.evaluate_utterance("todo bien")
    strong = gov.evaluate_utterance("sangrado abundante")
    merged = gov.merge(weak, strong)
    assert merged.severity == Severity.RED


def test_generative_cannot_weaken_floor() -> None:
    gov = SafetyGovernor()
    floor = gov.evaluate_utterance("dolor de pecho intenso")
    proposed = gov.evaluate_utterance("me siento mejor")
    enforced = gov.enforce_floor(proposed, floor)
    assert enforced.severity == Severity.RED
    assert "generative_override_blocked" in enforced.reasons
