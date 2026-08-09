"""PHASE 5B integration tests with mocked Ollama (no real models)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from evals.llm.benchmark import render_markdown
from evals.llm.preflight import run_preflight
from evals.llm.scorecard import recommend_primary_fallback


class _FakeResp:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> Any:
        return self._payload


def test_mocked_ollama_health_and_model_list() -> None:
    def fake_get(url: str, timeout: float = 0) -> _FakeResp:  # noqa: ARG001
        if url.endswith("/api/version"):
            return _FakeResp(200, {"version": "0.9.9-test"})
        if url.endswith("/api/tags"):
            return _FakeResp(
                200,
                {
                    "models": [
                        {
                            "name": "llama3.2:1b",
                            "digest": "sha256:test1",
                            "size": 111,
                            "details": {"quantization_level": "Q4_K_M", "parameter_size": "1B"},
                        }
                    ]
                },
            )
        raise AssertionError(url)

    def fake_post(url: str, json: dict | None = None, timeout: float = 0) -> _FakeResp:  # noqa: ARG001
        assert url.endswith("/api/show")
        return _FakeResp(
            200,
            {
                "details": {
                    "quantization_level": "Q4_K_M",
                    "parameter_size": "1B",
                    "family": "llama",
                },
                "size": 111,
            },
        )

    with (
        patch("evals.llm.preflight.httpx.get", side_effect=fake_get),
        patch("evals.llm.preflight.httpx.post", side_effect=fake_post),
        patch("evals.llm.preflight.shutil.which", return_value="/usr/bin/ollama"),
    ):
        report = run_preflight(base_url="http://127.0.0.1:11434")
    assert report.server_ok is True
    assert report.ollama_version == "0.9.9-test"
    installed = {c.candidate_id: c for c in report.candidates}
    assert installed["llama3.2:1b"].installed is True
    assert installed["llama3.2:3b"].installed is False
    assert installed["phi3.5"].installed is False


def test_unavailable_model_continues_in_recommendation() -> None:
    results = [
        {
            "status": "unavailable",
            "model_id": "llama3.2:1b",
            "availability": "UNAVAILABLE",
            "unavailable_reason": "model_not_installed",
        },
        {
            "status": "measured",
            "model_id": "llama3.2:3b",
            "resolved_tag": "llama3.2:3b",
            "availability": "AVAILABLE",
            "critical_safety_failures": 0,
            "safety_decision_contradiction_rate": 0.0,
            "unsupported_claim_rate": 0.05,
            "structured_output": {"schema_valid_rate": 0.85},
            "families": {
                "prompt_injection": {"pass_rate": 1.0},
                "colombian_spanish": {"pass_rate": 0.7},
                "noisy_conversation": {"pass_rate": 0.6},
                "evidence_grounded": {"pass_rate": 0.8},
            },
            "performance": {"warm_ttft_ms_p50": 200.0},
            "measured_case_count": 20,
            "advisory_risk": {"red_false_negatives": 0},
        },
        {
            "status": "unavailable",
            "model_id": "phi3.5",
            "availability": "UNAVAILABLE",
            "unavailable_reason": "candidate_failed:Timeout",
        },
    ]
    rec = recommend_primary_fallback(results)
    assert rec["PRIMARY_MODEL"] == "llama3.2:3b"
    assert rec["FALLBACK_MODEL"] is None


def test_report_generation_separates_official(tmp_path: Path) -> None:
    report = {
        "generated_at": "2026-01-01T00:00:00Z",
        "commit_sha": "abc",
        "manifest": {"benchmark_version": "5B.1", "commit_sha": "abc"},
        "official_dataset": {
            "OFFICIAL_DATASET": "UNAVAILABLE",
            "files_found": [],
            "evaluation_enabled": False,
        },
        "candidates": [
            {
                "candidate_id": "llama3.2:1b",
                "availability": "UNAVAILABLE",
                "status": "unavailable",
                "unavailable_reason": "ollama_unreachable",
            }
        ],
        "recommendation": {
            "PRIMARY_MODEL": None,
            "FALLBACK_MODEL": None,
            "reason": "insufficient_measured_evidence",
        },
    }
    md = render_markdown(report)
    assert "SYNTHETIC CONTROL RESULTS" in md
    assert "OFFICIAL DATASET RESULTS" in md
    assert "UNAVAILABLE" in md
    assert "PRIMARY_MODEL: `UNMEASURED`" in md or "PRIMARY_MODEL:" in md
    assert "None" not in md.split("PRIMARY_MODEL:")[1].split("\n")[0]


@pytest.mark.asyncio
async def test_candidate_failure_then_continuation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a raised failure for one candidate does not abort the loop logic."""
    from evals.llm import benchmark as bench

    calls: list[str] = []

    async def fake_bench(**kwargs: Any) -> dict[str, Any]:
        cid = kwargs["candidate"]["id"]
        calls.append(cid)
        if cid == "llama3.2:1b":
            raise RuntimeError("boom")
        return {
            "candidate_id": cid,
            "model_id": cid,
            "status": "measured",
            "availability": "AVAILABLE",
            "critical_safety_failures": 0,
            "safety_decision_contradiction_rate": 0.0,
            "unsupported_claim_rate": 0.0,
            "structured_output": {"schema_valid_rate": 1.0},
            "families": {},
            "family_scores": {},
            "measured_case_count": 20,
            "advisory_risk": {"red_false_negatives": 0},
            "performance": {},
        }

    monkeypatch.setattr(bench, "benchmark_candidate", fake_bench)
    monkeypatch.setattr(
        bench,
        "run_preflight",
        lambda base_url=None: MagicMock(
            ollama_version="test",
            ready_for_benchmark=True,
            server_ok=True,
            installed_models=["llama3.2:1b", "llama3.2:3b", "phi3.5"],
            blocking_reasons=[],
            operator_instructions=[],
            to_dict=lambda: {},
        ),
    )

    with patch("httpx.get", return_value=_FakeResp(200, {"models": []})):
        ns = MagicMock()
        ns.base_url = "http://127.0.0.1:11434"
        ns.repeats = 1
        ns.write_docs = False
        ns.json_out = str(Path("/tmp/limen-bench-test-latest.json"))
        ns.docs_out = str(Path("/tmp/limen-bench-test.md"))
        ns.run_dir = str(Path("/tmp/limen-bench-run"))
        ns.resume_dir = None
        # Force resolve to always find tags
        monkeypatch.setattr(
            bench,
            "_resolve_installed_tag",
            lambda available, tags: tags[0],
        )
        rc = await bench.async_main(ns)
    assert "llama3.2:1b" in calls
    assert "llama3.2:3b" in calls
    assert "phi3.5" in calls
    assert rc in (0, 2)
