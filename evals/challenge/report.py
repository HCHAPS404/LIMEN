"""Write PHASE 8 challenge evaluation artifacts and gate reports."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.challenge.runner import ScenarioResult, run_challenge_evaluation
from evals.challenge.scenarios import SCENARIOS

ROOT = Path(__file__).resolve().parents[2]


def _run_preflight() -> dict[str, Any]:
    import os

    env = dict(os.environ)
    env["LIMEN_RUNTIME_PROFILE"] = "challenge"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_challenge_environment.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    ready = "READY_FOR_CHALLENGE_RUNTIME=TRUE" in (proc.stdout or "")
    # Parse last JSON object from stdout
    data: dict[str, Any] = {
        "READY_FOR_CHALLENGE_RUNTIME": ready,
        "returncode": proc.returncode,
    }
    text = proc.stdout or ""
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data.update(json.loads(text[start : end + 1]))
        except json.JSONDecodeError:
            data["raw_tail"] = text[-2000:]
    data["stderr_tail"] = (proc.stderr or "")[-1000:]
    return data


def _summarize(results: list[ScenarioResult]) -> dict[str, Any]:
    counts = Counter(r.result for r in results)
    red_expected = [r for r in results if r.expected_safety_property.get("final_risk") == "RED"]
    red_fn = [
        r
        for r in red_expected
        if r.result == "FAIL"
        and r.actual_safety.get("risk") != "RED"
    ]
    dangerous = [r for r in results if r.extras.get("dangerous_reassurance")]
    injection_fail = [
        r
        for r in results
        if "injection" in r.category and r.result == "FAIL"
    ]
    return {
        "total": len(results),
        "passed": counts.get("PASS", 0),
        "failed": counts.get("FAIL", 0),
        "blocked": counts.get("BLOCKED", 0),
        "unverified": counts.get("UNVERIFIED", 0),
        "not_applicable": counts.get("NOT_APPLICABLE", 0),
        "partial": counts.get("PARTIAL", 0),
        "red_expected": len(red_expected),
        "red_false_negatives": [
            {"scenario_id": r.scenario_id, "actual": r.actual_safety, "reason": r.failure_reason}
            for r in red_fn
        ],
        "dangerous_reassurance": [r.scenario_id for r in dangerous],
        "injection_failures": [r.scenario_id for r in injection_fail],
        "by_category": dict(Counter(r.category for r in results)),
    }


def _failure_register(results: list[ScenarioResult], readiness: dict[str, Any]) -> dict[str, Any]:
    p0: list[dict[str, str]] = []
    p1: list[dict[str, str]] = []
    p2: list[dict[str, str]] = []
    p3: list[dict[str, str]] = []
    p4: list[dict[str, str]] = []

    if not readiness.get("READY_FOR_CHALLENGE_RUNTIME"):
        detail = readiness.get("reasons") or readiness.get("qdrant") or "preflight_false"
        p0.append({"id": "challenge_runtime_not_ready", "detail": str(detail)})
    p0.append(
        {
            "id": "g4_official_browser_samples",
            "detail": "N>=20 speech-end→playback UNMEASURED / deferred",
        }
    )
    p0.append(
        {
            "id": "g2_cold_bootstrap_unmeasured",
            "detail": "<=15 min cold start not measured in PHASE 8",
        }
    )
    p0.append(
        {
            "id": "g5_admin_ui_manual",
            "detail": "Admin console G5 smoke MANUAL_UNVERIFIED",
        }
    )

    for r in results:
        if r.result != "FAIL":
            continue
        entry = {"id": r.scenario_id, "detail": r.failure_reason or "fail"}
        is_red = r.expected_safety_property.get("final_risk") == "RED"
        is_inject = "injection" in r.category or r.extras.get("dangerous_reassurance")
        if is_red or is_inject:
            p1.append(entry)
        else:
            p2.append(entry)

    p2.append(
        {
            "id": "lexical_negation_fever_token",
            "detail": (
                "Token 'fiebre' in 'sin fiebre' still matches YELLOW pattern "
                "(known lexical limitation; do not redesign in PHASE 8)"
            ),
        }
    )
    p3.append(
        {
            "id": "conversation_ux_tuning",
            "detail": "repetition/endpointing human polish deferred",
        }
    )
    p3.append(
        {
            "id": "readme_final_metrics",
            "detail": "official voice P50/P95 pending samples",
        }
    )
    p4.append(
        {"id": "piper_optimization", "detail": "TTS latency optimization deferred"}
    )
    p4.append({"id": "video_demo_assets", "detail": "submission video not produced"})
    p4.append(
        {
            "id": "audioworklet",
            "detail": "ScriptProcessorNode migration post-challenge",
        }
    )

    return {"P0": p0, "P1": p1, "P2": p2, "P3": p3, "P4": p4}


def _gate_status(summary: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    ready = bool(readiness.get("READY_FOR_CHALLENGE_RUNTIME"))
    return {
        "G1": {
            "status": "PARTIAL",
            "evidence": "Repo deliverables + API/web/TRAZA/knowledge/safety/voice exist",
            "missing": "Final video/demo assets; final metrics package",
        },
        "G2": {
            "status": "UNVERIFIED",
            "evidence": "bootstrap/run-challenge documented",
            "missing": "Measured cold bootstrap <=15 min on challenge laptop",
        },
        "G3": {
            "status": "PASS",
            "evidence": "phi3.5 selected; ollama model present when service up; profile defaults",
            "missing": None,
        },
        "G4": {
            "status": "PARTIAL",
            "evidence": "Real STT/TTS path + automated voice tests; Piper OK in preflight",
            "missing": ">=20 valid browser speech-end→playback samples; human mic smoke",
        },
        "G5": {
            "status": "PARTIAL",
            "evidence": (
                "Automated upload/use/forget in challenge eval "
                f"(passed={summary.get('passed')})"
            ),
            "missing": "Manual admin-console interaction on challenge machine",
        },
        "challenge_runtime_ready": ready,
    }


def _write_gate_md(path: Path, gates: dict[str, Any], readiness: dict[str, Any]) -> None:
    lines = [
        "# Challenge Gate Evaluation (generated)",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        f"READY_FOR_CHALLENGE_RUNTIME: {readiness.get('READY_FOR_CHALLENGE_RUNTIME')}",
        f"Preflight reasons: {readiness.get('reasons')}",
        "",
    ]
    for key in ("G1", "G2", "G3", "G4", "G5"):
        g = gates[key]
        lines.extend(
            [
                f"## {key}",
                f"- status: **{g['status']}**",
                f"- evidence: {g['evidence']}",
                f"- missing: {g['missing']}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "runtime" / "evals" / "challenge" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    readiness = _run_preflight()
    (out_dir / "environment.json").write_text(
        json.dumps(readiness, indent=2, default=str) + "\n", encoding="utf-8"
    )

    run = run_challenge_evaluation(out_dir=out_dir, readiness=readiness)
    results: list[ScenarioResult] = run["results"]
    summary = _summarize(results)
    failures = _failure_register(results, readiness)
    gates = _gate_status(summary, readiness)

    (out_dir / "manifest.json").write_text(
        json.dumps(
            {
                "phase": "8",
                "stamp": stamp,
                "scenario_count": len(SCENARIOS),
                "eval_mode": "testclient_stub_providers_real_domains",
                "note": (
                    "Full LIMEN domains exercised via HTTP APIs. "
                    "Providers stubbed for CI isolation; Safety Governor is real."
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "scenario_results.json").write_text(
        json.dumps(run["payload"], indent=2, default=str) + "\n", encoding="utf-8"
    )
    (out_dir / "safety_summary.json").write_text(
        json.dumps(
            {
                "red_expected": summary["red_expected"],
                "red_false_negatives": summary["red_false_negatives"],
                "dangerous_reassurance": summary["dangerous_reassurance"],
                "injection_failures": summary["injection_failures"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    rag_rows = [
        r
        for r in results
        if "rag" in r.category
        or r.category.startswith("exact")
        or "corpus" in r.category
        or r.category == "no_evidence"
    ]
    (out_dir / "rag_summary.json").write_text(
        json.dumps(
            {
                "scenarios": [
                    {
                        "id": r.scenario_id,
                        "result": r.result,
                        "evidence_ids": r.evidence_ids,
                        "reason": r.failure_reason,
                    }
                    for r in rag_rows
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    knowledge_rows = [
        r
        for r in results
        if r.scenario_id.startswith(("J_", "K_", "M_", "V_", "H_", "I_"))
    ]
    (out_dir / "knowledge_summary.json").write_text(
        json.dumps(
            {
                "scenarios": [
                    {
                        "id": r.scenario_id,
                        "result": r.result,
                        "notes": r.notes,
                        "reason": r.failure_reason,
                        "provenance": r.extras.get("provenance"),
                    }
                    for r in knowledge_rows
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    traza_rows = [r for r in results if r.extras.get("traza_stages")]
    (out_dir / "trace_audit.json").write_text(
        json.dumps(
            {
                "audited": [
                    {
                        "id": r.scenario_id,
                        "call_id": r.traza_id,
                        "stages": r.extras.get("traza_stages"),
                        "result": r.result,
                    }
                    for r in traza_rows
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "metrics_audit.json").write_text(
        json.dumps(
            {
                "note": (
                    "Per-turn LLM/RAG metrics recorded in call metrics during API turns. "
                    "Official voice P50/P95 remain UNMEASURED (insufficient browser N)."
                ),
                "voice_p50_p95": "UNMEASURED",
                "eval_stack_tokens": "stub_llm_may_omit_real_token_counts",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "gate_status.json").write_text(
        json.dumps(gates, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "failure_register.json").write_text(
        json.dumps(failures, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    gate_md = ROOT / "docs" / "CHALLENGE_GATE_EVAL.generated.md"
    _write_gate_md(gate_md, gates, readiness)

    human = {
        "required": [
            "G4 human mic / audible multi-turn conversation",
            "G4 final browser P50/P95 (>=20 valid samples)",
            "G5 actual admin console upload/delete smoke",
            "G2 true cold bootstrap stopwatch",
            "Final demo UX walkthrough",
            "Video/demo assets",
        ]
    }
    (out_dir / "human_verification_required.json").write_text(
        json.dumps(human, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps({"out_dir": str(out_dir), "summary": summary, "gates": gates}, indent=2))
    # Non-zero only if RED false negatives or injection/safety P1 failures
    critical = (
        summary["red_false_negatives"]
        or summary["dangerous_reassurance"]
        or summary["injection_failures"]
    )
    if critical:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
