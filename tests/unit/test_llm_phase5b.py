"""PHASE 5B unit tests — no Ollama required."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evals.llm.identity import identity_from_tags_and_show
from evals.llm.manifest import build_manifest, manifest_fingerprint, manifests_compatible
from evals.llm.official_dataset import (
    PROHIBITED_GROUND_TRUTH_FIELDS,
    assert_no_ground_truth_in_prompt,
    discover_official_dataset,
    filter_model_input_fields,
)
from evals.llm.preflight import G3_LOCAL_CANDIDATES, run_preflight
from evals.llm.schemas import BenchmarkInterpretation
from evals.llm.scorecard import (
    compare_key,
    disqualification_reasons,
    recommend_primary_fallback,
)
from evals.llm.scoring import latency_summary

from limen.intelligence.providers.ollama import is_g3_allowed_ollama_model
from limen.intelligence.structured_output import parse_structured
from limen.telemetry.percentiles import p50, p95


def test_g3_candidate_allowlist_closed() -> None:
    assert G3_LOCAL_CANDIDATES == ("llama3.2:1b", "llama3.2:3b", "phi3.5")
    for mid in G3_LOCAL_CANDIDATES:
        assert is_g3_allowed_ollama_model(mid)
    for banned in ("llama3.3", "llama4", "phi4", "qwen2.5", "mistral", "gemma2", "gpt-oss"):
        assert not is_g3_allowed_ollama_model(banned)


def test_model_identity_does_not_guess() -> None:
    ident = identity_from_tags_and_show(
        requested_tag="llama3.2:1b",
        resolved_tag="llama3.2:1b",
        tags_payload={"models": [{"name": "llama3.2:1b", "digest": "sha256:abc", "size": 12}]},
        show_payload={"details": {}},
    )
    assert ident["digest"] == "sha256:abc"
    assert ident["artifact_size_bytes"] == 12
    assert ident["quantization"] == "UNMEASURED"

    empty = identity_from_tags_and_show(
        requested_tag="phi3.5",
        resolved_tag="phi3.5",
        tags_payload={"models": []},
        show_payload={},
    )
    assert empty["digest"] == "UNMEASURED"
    assert empty["artifact_size_bytes"] == "UNMEASURED"


def test_manifest_generation_and_fingerprint() -> None:
    m1 = build_manifest(
        temperature=0.2,
        max_tokens=256,
        repeats=3,
        case_ids=["a", "b"],
        dataset_sources=["synthetic_control_probes"],
        ollama_version="0.0.0",
    )
    assert m1["benchmark_version"]
    assert "password" not in json.dumps(m1).lower()
    assert "api_key" not in json.dumps(m1).lower()
    assert "secret" not in json.dumps(m1).lower() or "no api keys" in json.dumps(m1).lower()
    fp1 = manifest_fingerprint(m1)
    m2 = dict(m1)
    m2["generated_at"] = "other"
    assert manifest_fingerprint(m2) == fp1
    m3 = dict(m1)
    m3["temperature"] = 0.9
    assert not manifests_compatible(m1, m3)


def test_scorecard_safety_precedes_latency() -> None:
    safe_slow = {
        "status": "measured",
        "model_id": "llama3.2:3b",
        "resolved_tag": "llama3.2:3b",
        "critical_safety_failures": 0,
        "safety_decision_contradiction_rate": 0.0,
        "unsupported_claim_rate": 0.1,
        "structured_output": {"schema_valid_rate": 0.9},
        "families": {
            "prompt_injection": {"pass_rate": 1.0},
            "colombian_spanish": {"pass_rate": 0.8},
            "noisy_conversation": {"pass_rate": 0.8},
            "evidence_grounded": {"pass_rate": 0.8},
        },
        "performance": {"warm_ttft_ms_p50": 5000.0},
        "measured_case_count": 20,
        "advisory_risk": {"red_false_negatives": 0},
    }
    unsafe_fast = {
        "status": "measured",
        "model_id": "llama3.2:1b",
        "resolved_tag": "llama3.2:1b",
        "critical_safety_failures": 2,
        "safety_decision_contradiction_rate": 0.5,
        "unsupported_claim_rate": 0.0,
        "structured_output": {"schema_valid_rate": 1.0},
        "families": {
            "prompt_injection": {"pass_rate": 0.0},
            "colombian_spanish": {"pass_rate": 1.0},
            "noisy_conversation": {"pass_rate": 1.0},
            "evidence_grounded": {"pass_rate": 1.0},
        },
        "performance": {"warm_ttft_ms_p50": 10.0},
        "measured_case_count": 20,
        "advisory_risk": {"red_false_negatives": 3},
    }
    rec = recommend_primary_fallback([safe_slow, unsafe_fast])
    assert rec["PRIMARY_MODEL"] == "llama3.2:3b"
    assert disqualification_reasons(
        {
            "eligible": True,
            "g3_eligible": True,
            "critical_safety_failures": 1,
            "safety_decision_contradiction_rate": 0.0,
        }
    ) == ["critical_safety_failures"]


def test_primary_fallback_null_when_insufficient() -> None:
    rec = recommend_primary_fallback(
        [
            {
                "status": "unavailable",
                "model_id": "llama3.2:1b",
                "unavailable_reason": "ollama_unreachable",
            }
        ]
    )
    assert rec["PRIMARY_MODEL"] is None
    assert rec["FALLBACK_MODEL"] is None


def test_malformed_json_counts_as_failure() -> None:
    with pytest.raises(ValueError):
        parse_structured("not json {{{", BenchmarkInterpretation)


def test_percentile_calculations() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 100.0]
    assert p50(values) is not None
    assert p95(values) is not None
    summary = latency_summary(values)
    assert summary["p50_ms"] == p50(values)
    assert summary["p95_ms"] == p95(values)


def test_ground_truth_exclusion_from_model_input() -> None:
    record = {
        "patient_text": "me falta el aire",
        "label_ground_truth": "RED",
        "expected_risk": "RED",
        "trajectory_outcome": "hospital",
        "caso_id": "caso_99",
    }
    filtered = filter_model_input_fields(record)
    for field in PROHIBITED_GROUND_TRUTH_FIELDS:
        assert field not in {k.lower() for k in filtered}
    prompt = f"Paciente: {filtered.get('patient_text')}"
    assert_no_ground_truth_in_prompt(prompt, record)
    with pytest.raises(AssertionError):
        assert_no_ground_truth_in_prompt(
            "label_ground_truth=RED me falta el aire",
            None,
        )


def test_official_dataset_discovery_does_not_fabricate(tmp_path: Path) -> None:
    status = discover_official_dataset(tmp_path)
    assert status.status == "UNAVAILABLE"
    assert status.available is False
    assert status.evaluation_enabled is False
    assert status.resolution_order[-1] == "unavailable"
    assert status.fingerprints == []


def test_canonical_resolution_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from evals.llm.official_dataset import canonical_resolution_candidates

    monkeypatch.delenv("LIMEN_DATASET_PATH", raising=False)
    labels = [label for label, _ in canonical_resolution_candidates(tmp_path)]
    assert labels == ["./dataset/", "./data/challenge/"]
    monkeypatch.setenv("LIMEN_DATASET_PATH", str(tmp_path / "mounted"))
    labels2 = [label for label, _ in canonical_resolution_candidates(tmp_path)]
    assert labels2[0] == "LIMEN_DATASET_PATH"


def test_dataset_fingerprint_csv(tmp_path: Path) -> None:
    from evals.llm.official_dataset import fingerprint_dataset_file

    path = tmp_path / "dataset_final.csv"
    path.write_text("patient_text,label_ground_truth\nhola,RED\nadios,GREEN\n", encoding="utf-8")
    fp = fingerprint_dataset_file(path)
    assert fp.filename == "dataset_final.csv"
    assert len(fp.sha256) == 64
    assert fp.row_count == 2
    assert fp.columns == ["patient_text", "label_ground_truth"]


def test_discover_uses_dataset_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIMEN_DATASET_PATH", raising=False)
    ds = tmp_path / "dataset"
    ds.mkdir()
    (ds / "dataset_final.csv").write_text("texto\nx\n", encoding="utf-8")
    status = discover_official_dataset(tmp_path)
    assert status.status == "AVAILABLE"
    assert status.resolved_root == str(ds.resolve())
    assert status.fingerprints
    assert status.fingerprints[0]["filename"] == "dataset_final.csv"


def test_stale_result_rejection() -> None:
    a = build_manifest(
        temperature=0.2,
        max_tokens=256,
        repeats=3,
        case_ids=["x"],
        dataset_sources=["synthetic_control_probes"],
        ollama_version="1",
    )
    b = dict(a)
    b["commit_sha"] = "deadbeef"
    assert not manifests_compatible(a, b)


def test_preflight_reports_without_ollama() -> None:
    report = run_preflight(base_url="http://127.0.0.1:9")
    assert report.server_ok is False
    assert report.ready_for_benchmark is False
    assert len(report.candidates) == 3


def test_compare_key_orders_disqualified_last() -> None:
    good = {
        "eligible": True,
        "g3_eligible": True,
        "critical_safety_failures": 0,
        "safety_decision_contradiction_rate": 0.0,
        "red_false_negatives": 0,
        "unsupported_claim_rate": 0.1,
        "schema_valid_rate": 0.9,
        "evidence_grounding_pass_rate": 0.9,
        "spanish_pass_rate": 0.9,
        "noisy_pass_rate": 0.9,
        "injection_resist_rate": 1.0,
        "warm_latency_p50_ms": 100.0,
        "ram_rss_delta_bytes": 1,
    }
    bad = dict(good)
    bad["critical_safety_failures"] = 5
    assert compare_key(good) < compare_key(bad)
