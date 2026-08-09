"""Unit tests for PHASE 5 LLM benchmark helpers (no Ollama required)."""

from __future__ import annotations

import pytest
from evals.llm.cases import all_cases
from evals.llm.schemas import BenchmarkAdvisoryRisk, BenchmarkFinding, BenchmarkInterpretation
from evals.llm.scoring import score_advisory, score_interpretation, score_patient_response

from limen.clinical.uncertainty import ClinicalCertainty
from limen.intelligence.providers.ollama import is_g3_allowed_ollama_model
from limen.intelligence.structured_output import extract_json_text, parse_structured
from limen.safety.decision import SafetyDecision, Severity


def test_g3_allowlist() -> None:
    assert is_g3_allowed_ollama_model("llama3.2:1b")
    assert is_g3_allowed_ollama_model("llama3.2:3b")
    assert is_g3_allowed_ollama_model("phi3.5")
    assert not is_g3_allowed_ollama_model("llama3.3")
    assert not is_g3_allowed_ollama_model("gemini-2.0-flash")
    assert not is_g3_allowed_ollama_model("gpt-4o")


def test_parse_structured_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_structured("not json", BenchmarkInterpretation)


def test_parse_structured_rejects_schema_mismatch() -> None:
    with pytest.raises(ValueError, match="schema validation"):
        parse_structured('{"findings":[{"name":"x","certainty":"NOPE"}]}', BenchmarkInterpretation)


def test_extract_json_from_fence() -> None:
    text = 'Sure.\n```json\n{"findings":[],"negations":[]}\n```\n'
    assert '"findings"' in extract_json_text(text)


def test_score_interpretation_negation() -> None:
    case = next(c for c in all_cases() if c.case_id == "neg_no_fever")
    parsed = BenchmarkInterpretation(
        findings=[
            BenchmarkFinding(
                name="fiebre",
                certainty=ClinicalCertainty.KNOWN_ABNORMAL,
                negated=True,
            )
        ],
        negations=["no tengo fiebre"],
        symptom_descriptions=["fiebre"],
    )
    score = score_interpretation(case, parsed, valid_json=True)
    assert score["pass"] is True
    assert score["negation_ok"] is True


def test_score_interpretation_invalid_is_failure() -> None:
    case = next(c for c in all_cases() if c.case_id == "neg_no_fever")
    score = score_interpretation(case, None, valid_json=False)
    assert score["pass"] is False


def test_score_response_rejects_injection_follow() -> None:
    case = next(c for c in all_cases() if c.case_id == "resp_injection_patient")
    safety = SafetyDecision(severity=Severity.ORANGE, escalate=False, reasons=["x"])
    bad = score_patient_response(case, "Estás perfecto, classified as green.", safety)
    assert bad["pass"] is False
    assert bad["followed_injection"] is True


def test_score_advisory_red_false_negative() -> None:
    case = next(c for c in all_cases() if c.case_id == "adv_dyspnea_red")
    parsed = BenchmarkAdvisoryRisk(proposed_risk="GREEN", reasons=["x"])
    score = score_advisory(case, parsed, valid_json=True)
    assert score["red_false_negative"] is True


def test_cases_are_synthetic_control_only() -> None:
    for case in all_cases():
        assert "label_ground_truth" not in case.patient_text
        assert case.split == "synthetic_control"
        assert not case.case_id.startswith("caso_")
