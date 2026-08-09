"""Negation-aware Safety floor — fever denied must not false-positive YELLOW."""

from __future__ import annotations

from limen.clinical.extraction import extract_from_utterance
from limen.clinical.state import ClinicalState, Finding
from limen.clinical.uncertainty import ClinicalCertainty
from limen.conversation.orchestrator import ConversationOrchestrator
from limen.safety.decision import Severity
from limen.safety.governor import SafetyGovernor
from limen.safety.rules import evaluate_state_rules, evaluate_text_rules


def test_efecto_de_fiebre_negation_is_not_abnormal() -> None:
    text = "No me está causando un efecto de fiebre, pero sí me da mareo"
    state = extract_from_utterance(text)
    fever = next(f for f in state.findings if f.name == "fever")
    assert fever.certainty == ClinicalCertainty.KNOWN_NORMAL
    decision = evaluate_text_rules(text)
    assert not any("yellow_pattern:\\bfiebre\\b" in r for r in decision.reasons)


def test_sin_fiebre_is_not_yellow_from_lexical_token() -> None:
    decision = evaluate_text_rules("Sin fiebre y dolor leve en la herida.")
    assert not any("yellow_pattern:\\bfiebre\\b" in r for r in decision.reasons)


def test_tengo_fiebre_remains_yellow() -> None:
    decision = evaluate_text_rules("Tengo fiebre desde anoche.")
    assert decision.severity == Severity.YELLOW


def test_state_fever_abnormal_is_yellow() -> None:
    state = ClinicalState(
        findings=[
            Finding(name="fever", certainty=ClinicalCertainty.KNOWN_ABNORMAL),
        ]
    )
    decision = evaluate_state_rules(state)
    assert decision.severity == Severity.YELLOW


def test_state_fever_normal_is_not_yellow() -> None:
    state = ClinicalState(
        findings=[
            Finding(name="fever", certainty=ClinicalCertainty.KNOWN_NORMAL),
        ]
    )
    decision = evaluate_state_rules(state)
    assert decision.severity == Severity.GREEN


def test_governor_merge_negation_with_wound_heat() -> None:
    gov = SafetyGovernor()
    text = "No tengo fiebre. La herida está caliente y roja, me duele."
    state = extract_from_utterance(text)
    floor = gov.merge(gov.evaluate_utterance(text), gov.evaluate_state(state))
    fever = next(f for f in state.findings if f.name == "fever")
    assert fever.certainty == ClinicalCertainty.KNOWN_NORMAL
    assert floor.severity < Severity.RED
    assert not any("yellow_pattern:\\bfiebre\\b" in r for r in floor.reasons)


def test_conflict_after_negation_stays_conservative_yellow() -> None:
    gov = SafetyGovernor()
    state = extract_from_utterance("No tengo fiebre.")
    state = extract_from_utterance("Me midieron 38.7, creo que sí tengo fiebre.", state)
    fever = next(f for f in state.findings if f.name == "fever")
    assert fever.certainty == ClinicalCertainty.CONFLICTING
    floor = gov.merge(
        gov.evaluate_utterance("Me midieron 38.7, creo que sí tengo fiebre."),
        gov.evaluate_state(state),
    )
    assert floor.severity >= Severity.YELLOW


def test_red_unaffected_by_fever_negation() -> None:
    gov = SafetyGovernor()
    text = "No tengo fiebre pero no puedo respirar."
    state = extract_from_utterance(text)
    floor = gov.merge(gov.evaluate_utterance(text), gov.evaluate_state(state))
    assert floor.severity == Severity.RED
    assert floor.escalate is True


def test_breathing_and_bleeding_negation_not_red() -> None:
    gov = SafetyGovernor()
    text = "No me falta el aire. No estoy sangrando. Solo dolor leve."
    state = extract_from_utterance(text)
    floor = gov.merge(gov.evaluate_utterance(text), gov.evaluate_state(state))
    assert floor.severity < Severity.RED
    assert floor.escalate is False


async def test_orchestrator_negation_floor_green() -> None:
    orch = ConversationOrchestrator()
    result = await orch.handle_text_turn(
        call_id="c1",
        account_id="a1",
        user_text="No tengo fiebre.",
        clinical_state=ClinicalState(),
    )
    assert result.safety.severity == Severity.GREEN
    fever = next(f for f in result.clinical_state.findings if f.name == "fever")
    assert fever.certainty == ClinicalCertainty.KNOWN_NORMAL
