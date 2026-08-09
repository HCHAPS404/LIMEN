"""PHASE 5C integrity unit tests (no Ollama required)."""

from __future__ import annotations

from evals.llm.failures import injection_metrics_from_cases
from evals.llm.metrics import display, tokens_per_second_ollama
from evals.llm.official_dataset import firewall_prompt
from evals.llm.scorecard import recommend_primary_fallback


def test_display_never_none() -> None:
    assert display(None) == "UNMEASURED"
    assert display(0.5) == 0.5


def test_tokens_per_second_ollama_native_only() -> None:
    assert tokens_per_second_ollama(completion_tokens=50, eval_duration_ns=1_000_000_000) == 50.0
    assert tokens_per_second_ollama(completion_tokens=None, eval_duration_ns=1e9) is None
    assert tokens_per_second_ollama(completion_tokens=10, eval_duration_ns=None) is None


def test_injection_metrics_patient_vs_evidence() -> None:
    cases = [
        {
            "case_id": "resp_injection_patient",
            "family": "prompt_injection",
            "response": {"followed_injection": False, "pass": True},
        },
        {
            "case_id": "resp_injection_doc",
            "family": "prompt_injection",
            "response": {"followed_injection": True, "pass": False},
        },
    ]
    inj = injection_metrics_from_cases(cases)
    assert inj["patient_side"]["resist_rate"] == 1.0
    assert inj["evidence_side"]["attack_success_rate"] == 1.0
    assert inj["overall_resist_rate"] == 0.5
    assert inj["n"] == 2


def test_recommendation_rationale_not_none_when_selected() -> None:
    results = [
        {
            "status": "measured",
            "model_id": "llama3.2:3b",
            "resolved_tag": "llama3.2:3b",
            "critical_safety_failures": 0,
            "safety_decision_contradiction_rate": 0.0,
            "unsupported_claim_rate": 0.0,
            "structured_output": {"schema_valid_rate": 1.0},
            "injection": {"overall_resist_rate": 1.0},
            "families": {
                "prompt_injection": {"pass_rate": 1.0, "n": 2},
                "colombian_spanish": {"pass_rate": 0.5},
                "noisy_conversation": {"pass_rate": 0.5},
                "evidence_grounded": {"pass_rate": 1.0},
            },
            "performance": {"warm_ttft_ms_p50": 10.0, "generation_latency_ms_p50": 100.0},
            "measured_case_count": 20,
            "advisory_risk": {"red_false_negatives": 0},
        },
        {
            "status": "measured",
            "model_id": "llama3.2:1b",
            "resolved_tag": "llama3.2:1b",
            "critical_safety_failures": 0,
            "safety_decision_contradiction_rate": 0.0,
            "unsupported_claim_rate": 0.0,
            "structured_output": {"schema_valid_rate": 0.05},
            "injection": {"overall_resist_rate": 1.0},
            "families": {
                "prompt_injection": {"pass_rate": 1.0, "n": 2},
                "colombian_spanish": {"pass_rate": 0.0},
                "noisy_conversation": {"pass_rate": 0.0},
                "evidence_grounded": {"pass_rate": 1.0},
            },
            "performance": {"generation_latency_ms_p50": 50.0},
            "measured_case_count": 20,
            "advisory_risk": {"red_false_negatives": 1},
        },
    ]
    rec = recommend_primary_fallback(results, official_red_available=False)
    assert rec["PRIMARY_MODEL"] == "llama3.2:3b"
    assert rec["STATUS"] == "PROVISIONAL"
    assert rec["reason"] is not None
    assert "None" != rec["reason"]
    assert "PRIMARY=llama3.2:3b" in rec["rationale"]
    assert rec["candidate_roles"].get("llama3.2:1b") == "BASELINE_ONLY / NOT_RECOMMENDED"


def test_firewall_blocks_ground_truth_leak() -> None:
    try:
        firewall_prompt("label_ground_truth=RED patient says pain")
        raised = False
    except AssertionError:
        raised = True
    assert raised
    assert firewall_prompt("Paciente: me duele la herida.") == "Paciente: me duele la herida."
