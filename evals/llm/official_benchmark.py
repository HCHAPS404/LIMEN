#!/usr/bin/env python3
"""PHASE 5C.2 — official dataset dry-run + advisory benchmark runner."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.llm.identity import identity_from_tags_and_show
from evals.llm.manifest import BENCHMARK_VERSION, build_manifest, git_sha
from evals.llm.metrics import display
from evals.llm.official_dataset import (
    discover_official_dataset,
    fingerprint_dataset_file,
    firewall_prompt,
)
from evals.llm.official_load import (
    RESULT_SHEET,
    load_official_tables,
    resolve_official_paths,
)
from evals.llm.official_metrics import score_official_prediction, summarize_official_results
from evals.llm.official_reconstruct import (
    ReconstructedOfficialDataset,
    build_transcript,
    reconstruct_official_dataset,
)
from evals.llm.preflight import default_base_url, run_preflight
from evals.llm.prompts import ADVISORY_RISK_SYSTEM, official_advisory_user_prompt
from evals.llm.schemas import BenchmarkAdvisoryRisk
from evals.llm.scorecard import recommend_primary_fallback

from limen.intelligence.contracts import LLMRequest
from limen.intelligence.providers.ollama import OllamaLLMProvider

CANDIDATES = (
    {"id": "llama3.2:1b", "ollama_tags": ("llama3.2:1b",)},
    {"id": "llama3.2:3b", "ollama_tags": ("llama3.2:3b",)},
    {"id": "phi3.5", "ollama_tags": ("phi3.5", "phi3.5:latest", "phi3.5:3.8b")},
)

TEMPERATURE = 0.2
MAX_TOKENS = 256
KEEP_ALIVE_UNLOAD = 0
BENCH_ROOT = ROOT / "runtime" / "benchmarks" / "llm"
FINGERPRINT_PATH = BENCH_ROOT / "dataset_fingerprint.json"
DRY_RUN_PATH = BENCH_ROOT / "official_dry_run.json"
DOCS_PATH = ROOT / "docs" / "LLM_BENCHMARK_OFFICIAL.generated.md"
SYNTHETIC_LATEST = BENCH_ROOT / "latest.json"


def _resolve_installed_tag(available: list[str], tags: tuple[str, ...]) -> str | None:
    available_l = {a.lower(): a for a in available}
    for tag in tags:
        if tag.lower() in available_l:
            return available_l[tag.lower()]
        for installed_l, original in available_l.items():
            if installed_l.startswith(f"{tag.lower()}@"):
                return original
    return None


def dataset_fingerprint_digest(fingerprints: list[dict[str, Any]]) -> str:
    payload = json.dumps(fingerprints, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def case_cache_key(
    *,
    case_id: str,
    layer: str,
    commit_sha: str | None,
    dataset_sha: str,
    model_digest: str,
    temperature: float,
    max_tokens: int,
) -> str:
    parts = [
        BENCHMARK_VERSION,
        commit_sha or "NO_SHA",
        dataset_sha,
        model_digest,
        str(temperature),
        str(max_tokens),
        case_id,
        layer,
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def run_official_dry_run(project_root: Path | None = None) -> dict[str, Any]:
    """Inspect, reconstruct, validate — no LLM calls."""
    base = project_root or ROOT
    discovery = discover_official_dataset(base)
    report: dict[str, Any] = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "benchmark_version": BENCHMARK_VERSION,
        "discovery": discovery.to_dict(),
        "sheet_required": RESULT_SHEET,
        "ready_for_official_benchmark": False,
        "validation_errors": [],
        "reconstruction_stats": {},
        "field_classification": {},
        "firewall_samples": [],
    }

    if not discovery.available or not discovery.resolved_root:
        report["validation_errors"].append("official_dataset_unavailable")
        return report

    paths = resolve_official_paths(Path(discovery.resolved_root))
    if paths is None:
        report["validation_errors"].append("missing_one_or_more_canonical_xlsx")
        return report

    try:
        tables = load_official_tables(paths)
    except Exception as exc:
        report["validation_errors"].append(f"load_failed:{type(exc).__name__}:{exc}")
        return report

    reconstructed = reconstruct_official_dataset(tables)
    report["reconstruction_stats"] = reconstructed.stats
    report["field_classification"] = tables.field_classification
    report["validation_errors"].extend(reconstructed.validation_errors)

    # Firewall on sample prompts built from first conversation.
    if reconstructed.conversations:
        sample = reconstructed.conversations[0]
        transcript = build_transcript(sample)
        prompt = official_advisory_user_prompt(transcript, sample.known_clinical_profile)
        try:
            firewall_prompt(prompt, purpose="official_dry_run_sample")
            report["firewall_samples"].append({"case_id": sample.case_id, "passed": True})
        except AssertionError as exc:
            report["firewall_samples"].append(
                {"case_id": sample.case_id, "passed": False, "error": str(exc)}
            )
            report["validation_errors"].append(f"firewall_sample_failed:{sample.case_id}")

    report["fingerprints"] = [
        fingerprint_dataset_file(Path(p)).to_dict()
        for p in [
            paths.dataset_final,
            paths.trayectorias,
            paths.perfiles_clinicos,
            paths.perfiles_pacientes_co,
        ]
    ]
    report["dataset_sha256"] = dataset_fingerprint_digest(report["fingerprints"])

    ready = not report["validation_errors"]
    report["ready_for_official_benchmark"] = ready
    report["conversation_count"] = len(reconstructed.conversations)
    return report


def write_dry_run_artifacts(report: dict[str, Any]) -> None:
    BENCH_ROOT.mkdir(parents=True, exist_ok=True)
    FINGERPRINT_PATH.write_text(
        json.dumps(
            {
                "generated_at": report.get("generated_at"),
                "benchmark_version": BENCHMARK_VERSION,
                "fingerprints": report.get("fingerprints", []),
                "dataset_sha256": report.get("dataset_sha256"),
                "ready_for_official_benchmark": report.get("ready_for_official_benchmark"),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    DRY_RUN_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _truth_by_case_layer(
    reconstructed: ReconstructedOfficialDataset,
) -> dict[tuple[str, str], Any]:
    return {(t.case_id, t.layer): t for t in reconstructed.truths}


async def _unload_model(base_url: str, model: str) -> None:
    import httpx

    async with httpx.AsyncClient(timeout=60.0) as client:
        await client.post(
            f"{base_url.rstrip('/')}/api/generate",
            json={"model": model, "keep_alive": KEEP_ALIVE_UNLOAD, "prompt": "", "stream": False},
        )


def _load_cached_case(path: Path, expected_key: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("cache_key") == expected_key and data.get("status") == "completed":
        return data
    return None


async def benchmark_official_model(
    *,
    candidate: dict[str, Any],
    model_tag: str,
    base_url: str,
    reconstructed: ReconstructedOfficialDataset,
    dataset_sha: str,
    run_dir: Path,
    resume_dir: Path | None,
    tags_payload: dict[str, Any] | None,
    show_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    cand_id = str(candidate["id"])
    identity = identity_from_tags_and_show(
        requested_tag=cand_id,
        resolved_tag=model_tag,
        tags_payload=tags_payload,
        show_payload=show_payload,
    )
    model_digest = str(identity.get("digest") or "UNMEASURED")
    commit = git_sha()
    truths = _truth_by_case_layer(reconstructed)
    # Ensure prior residents are unloaded before cold/advisory work.
    await _unload_model(base_url, model_tag)
    provider = OllamaLLMProvider(base_url=base_url, model=model_tag)
    case_results: list[dict[str, Any]] = []
    total = len(reconstructed.conversations)
    t0 = time.perf_counter()

    for idx, conversation in enumerate(reconstructed.conversations, start=1):
        truth = truths[(conversation.case_id, conversation.layer)]
        cache_key = case_cache_key(
            case_id=conversation.case_id,
            layer=conversation.layer,
            commit_sha=commit,
            dataset_sha=dataset_sha,
            model_digest=model_digest,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        cache_path = run_dir / "cases" / cand_id.replace(":", "-") / f"{cache_key}.json"
        if resume_dir:
            resume_path = resume_dir / "cases" / cand_id.replace(":", "-") / f"{cache_key}.json"
            cached = _load_cached_case(resume_path, cache_key)
            if cached:
                case_results.append(cached)
                if idx == 1 or idx % 20 == 0 or idx == total:
                    print(f"[{cand_id}] case {idx}/{total} (cached)", flush=True)
                continue

        if idx == 1 or idx % 20 == 0 or idx == total:
            elapsed = time.perf_counter() - t0
            rate = idx / elapsed if elapsed > 0 else 0.0
            remaining = (total - idx) / rate if rate > 0 else None
            eta = f" ETA≈{remaining:.0f}s" if remaining is not None else ""
            print(f"[{cand_id}] case {idx}/{total}{eta}", flush=True)

        transcript = build_transcript(conversation)
        prompt = official_advisory_user_prompt(transcript, conversation.known_clinical_profile)
        firewall_prompt(prompt, purpose="official_advisory")

        parsed = None
        valid = False
        error: str | None = None
        try:
            parsed, _responses = await provider.generate_structured_tracked(
                LLMRequest(
                    prompt=prompt,
                    system=firewall_prompt(
                        ADVISORY_RISK_SYSTEM, purpose="official_advisory_system"
                    ),
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    metadata={
                        "purpose": "official_advisory_benchmark",
                        "case_id": conversation.case_id,
                        "layer": conversation.layer,
                    },
                ),
                BenchmarkAdvisoryRisk,
                max_attempts=2,
            )
            valid = True
        except Exception as exc:
            error = f"{type(exc).__name__}:{exc}"

        predicted = parsed.proposed_risk if parsed else None
        scored = score_official_prediction(
            ground_truth=truth.label_normalized,  # type: ignore[arg-type]
            predicted=predicted,
            valid_json=valid,
        )
        entry = {
            "cache_key": cache_key,
            "status": "completed",
            "case_id": conversation.case_id,
            "layer": conversation.layer,
            "patient_id": conversation.patient_id,
            "ground_truth": truth.label_normalized,
            "predicted": scored.get("predicted"),
            "exact_match": scored.get("exact_match"),
            "red_false_negative": scored.get("red_false_negative"),
            "valid_schema": scored.get("valid_schema"),
            "error": error,
        }
        case_results.append(entry)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(entry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    await _unload_model(base_url, model_tag)
    metrics = summarize_official_results(case_results)
    schema_valid_rate = (
        sum(1 for c in case_results if c.get("valid_schema")) / len(case_results)
        if case_results
        else None
    )
    return {
        "candidate_id": cand_id,
        "model_id": cand_id,
        "resolved_tag": model_tag,
        "status": "measured",
        "availability": "AVAILABLE",
        "identity": identity,
        "measured_case_count": len(case_results),
        "case_results": case_results,
        "official_advisory": metrics,
        "official_red_false_negatives": metrics["overall"]["red_false_negatives"],
        "official_red_recall": metrics["overall"]["red_recall"],
        "official_macro_f1": metrics["overall"]["macro_f1"],
        "official_accuracy": metrics["overall"]["accuracy"],
        "official_noisy_degradation": metrics["degradation"],
        "structured_output": {"schema_valid_rate": schema_valid_rate},
        "red_fn_breakdown": _red_fn_breakdown(case_results),
        "runtime_placement": "UNMEASURED",
    }


def _load_synthetic_latest() -> dict[str, Any] | None:
    if not SYNTHETIC_LATEST.is_file():
        return None
    try:
        return json.loads(SYNTHETIC_LATEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _merge_scorecard_inputs(
    official_results: list[dict[str, Any]], synthetic_latest: dict[str, Any] | None
) -> list[dict[str, Any]]:
    synthetic_by_model: dict[str, dict[str, Any]] = {}
    if synthetic_latest:
        for cand in synthetic_latest.get("candidates") or []:
            mid = str(cand.get("model_id") or cand.get("candidate_id") or "")
            if mid:
                synthetic_by_model[mid] = cand

    merged: list[dict[str, Any]] = []
    for official in official_results:
        mid = str(official.get("model_id") or "")
        base = dict(synthetic_by_model.get(mid, {}))
        base.update(official)
        base["official_red_false_negatives"] = official.get("official_red_false_negatives")
        base["official_macro_f1"] = official.get("official_macro_f1")
        base["official_red_recall"] = official.get("official_red_recall")
        base["official_noisy_degradation"] = official.get("official_noisy_degradation")
        base["status"] = official.get("status")
        base["model_id"] = mid
        merged.append(base)
    return merged


def _red_fn_breakdown(rows: list[dict[str, Any]]) -> dict[str, Any]:
    red_rows = [r for r in rows if r.get("ground_truth") == "RED"]
    fns = [r for r in red_rows if r.get("red_false_negative")]
    to_green = sum(1 for r in fns if r.get("predicted") == "GREEN")
    to_yellow = sum(1 for r in fns if r.get("predicted") == "YELLOW")
    to_orange = sum(1 for r in fns if r.get("predicted") == "ORANGE")
    to_none = sum(1 for r in fns if r.get("predicted") is None)
    return {
        "count": len(fns),
        "total_red": len(red_rows),
        "rate": (len(fns) / len(red_rows)) if red_rows else None,
        "became_green": to_green,
        "became_yellow": to_yellow,
        "became_orange": to_orange,
        "invalid_or_missing": to_none,
    }


def render_official_docs(summary: dict[str, Any]) -> str:
    lines = [
        "# LLM Benchmark — Official Dataset (generated) — PHASE 5C.2",
        "",
        f"Generated at: `{summary.get('generated_at')}`",
        f"Benchmark version: `{summary.get('benchmark_version')}`",
        f"Dataset SHA256: `{display(summary.get('dataset_sha256'))}`",
        "",
        "## Overall official results",
        "",
        ("| Model | Accuracy | Macro F1 | GREEN R | YELLOW R | RED R | RED FN | Schema valid |"),
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cand in summary.get("candidates") or []:
        mid = cand.get("model_id")
        metrics = cand.get("official_advisory") or {}
        overall = metrics.get("overall") or {}
        per = overall.get("per_class") or {}
        schema_rate = None
        cases = cand.get("case_results") or []
        if cases:
            schema_rate = sum(1 for c in cases if c.get("valid_schema")) / len(cases)
        lines.append(
            "| {m} | {a} | {f1} | {g} | {y} | {r} | {fn} | {sv} |".format(
                m=mid,
                a=display(overall.get("accuracy")),
                f1=display(overall.get("macro_f1")),
                g=display((per.get("GREEN") or {}).get("recall")),
                y=display((per.get("YELLOW") or {}).get("recall")),
                r=display(overall.get("red_recall")),
                fn=display(overall.get("red_false_negatives")),
                sv=display(schema_rate),
            )
        )

    lines.extend(["", "## Clean / Noisy / Degradation", ""])
    for cand in summary.get("candidates") or []:
        mid = cand.get("model_id")
        metrics = cand.get("official_advisory") or {}
        clean = metrics.get("clean") or {}
        noisy = metrics.get("noisy") or {}
        deg = metrics.get("degradation") or {}
        lines.extend(
            [
                f"### {mid}",
                f"- clean macro F1: `{display(clean.get('macro_f1'))}` "
                f"accuracy=`{display(clean.get('accuracy'))}` "
                f"RED FN=`{display(clean.get('red_false_negatives'))}`",
                f"- noisy macro F1: `{display(noisy.get('macro_f1'))}` "
                f"accuracy=`{display(noisy.get('accuracy'))}` "
                f"RED FN=`{display(noisy.get('red_false_negatives'))}`",
                f"- degradation: `{display(deg)}`",
                "",
            ]
        )

    lines.extend(["", "## RED false-negative breakdown", ""])
    for cand in summary.get("candidates") or []:
        mid = cand.get("model_id")
        breakdown = _red_fn_breakdown(cand.get("case_results") or [])
        lines.append(
            f"- **{mid}**: count={breakdown['count']}/"
            f"{breakdown['total_red']} rate={display(breakdown['rate'])} "
            f"→GREEN={breakdown['became_green']} "
            f"→YELLOW={breakdown['became_yellow']} "
            f"→ORANGE={breakdown['became_orange']} "
            f"invalid={breakdown['invalid_or_missing']}"
        )

    rec = summary.get("recommendation") or {}
    lines.extend(
        [
            "",
            "## Selection",
            "",
            f"- STATUS: `{display(rec.get('STATUS'))}`",
            f"- PRIMARY: `{display(rec.get('PRIMARY_MODEL'))}`",
            f"- FALLBACK: `{display(rec.get('FALLBACK_MODEL'))}`",
            "",
            rec.get("rationale") or rec.get("reason") or "UNMEASURED",
            "",
            "Synthetic-only report remains in `docs/LLM_BENCHMARK.generated.md`.",
            "Production LLM default is NOT switched (PHASE 5.1 not started).",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


async def async_main(args: argparse.Namespace) -> int:
    dry = run_official_dry_run()
    write_dry_run_artifacts(dry)
    ready = bool(dry.get("ready_for_official_benchmark"))
    print(f"READY_FOR_OFFICIAL_BENCHMARK={'TRUE' if ready else 'FALSE'}", flush=True)
    if not ready:
        for err in dry.get("validation_errors") or []:
            print(f"  - {err}", flush=True)
        return 2 if args.require_ready else 0

    if args.dry_run_only:
        return 0

    base_url = (args.base_url or default_base_url()).rstrip("/")
    preflight = run_preflight(base_url=base_url)
    if not preflight.ready_for_benchmark:
        print("Ollama preflight failed:", "; ".join(preflight.blocking_reasons), flush=True)
        return 1

    paths = resolve_official_paths(Path(dry["discovery"]["resolved_root"]))
    if paths is None:
        print("Official paths missing after dry-run.", flush=True)
        return 2
    tables = load_official_tables(paths)
    reconstructed = reconstruct_official_dataset(tables)
    dataset_sha = str(dry.get("dataset_sha256") or "")

    run_id = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.run_dir) if args.run_dir else BENCH_ROOT / "runs" / f"official_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    resume_dir = Path(args.resume_dir) if args.resume_dir else None

    manifest = build_manifest(
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        repeats=1,
        case_ids=[f"{c.case_id}:{c.layer}" for c in reconstructed.conversations],
        dataset_sources=["official_tech_sphere_phase5c2"],
        ollama_version=preflight.ollama_version,
        candidate_models=[c["id"] for c in CANDIDATES],
        base_url=base_url,
        extra={
            "benchmark_kind": "official_advisory",
            "dataset_sha256": dataset_sha,
            "conversation_count": len(reconstructed.conversations),
        },
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (run_dir / "dataset_fingerprint.json").write_text(
        json.dumps(
            {
                "fingerprints": dry.get("fingerprints"),
                "dataset_sha256": dataset_sha,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    tags_payload: dict[str, Any] | None = None
    try:
        import httpx

        resp = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            tags_payload = resp.json()
    except Exception:
        tags_payload = None

    results: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        cand_id = candidate["id"]
        tag = _resolve_installed_tag(list(preflight.installed_models), candidate["ollama_tags"])
        if tag is None:
            results.append(
                {
                    "candidate_id": cand_id,
                    "model_id": cand_id,
                    "status": "unavailable",
                    "availability": "UNAVAILABLE",
                    "unavailable_reason": "model_not_installed",
                }
            )
            continue
        show_payload: dict[str, Any] | None = None
        try:
            import httpx

            show_resp = httpx.post(f"{base_url}/api/show", json={"name": tag}, timeout=30.0)
            if show_resp.status_code == 200:
                show_payload = show_resp.json()
        except Exception:
            show_payload = None

        print(f"Official benchmark {cand_id} as {tag} ...", flush=True)
        result = await benchmark_official_model(
            candidate=candidate,
            model_tag=tag,
            base_url=base_url,
            reconstructed=reconstructed,
            dataset_sha=dataset_sha,
            run_dir=run_dir,
            resume_dir=resume_dir,
            tags_payload=tags_payload,
            show_payload=show_payload,
        )
        results.append(result)
        (run_dir / f"{cand_id.replace(':', '-')}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    measured_models = [r for r in results if r.get("status") == "measured"]
    official_complete = len(measured_models) == len(CANDIDATES)
    synthetic_latest = _load_synthetic_latest()
    scorecard_inputs = _merge_scorecard_inputs(results, synthetic_latest)
    recommendation = recommend_primary_fallback(
        scorecard_inputs,
        official_red_available=official_complete,
        official_eval_complete=official_complete,
    )

    summary = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "benchmark_version": BENCHMARK_VERSION,
        "phase": "5C.2",
        "dataset_sha256": dataset_sha,
        "dry_run": dry,
        "manifest": manifest,
        "candidates": results,
        "recommendation": recommendation,
        "synthetic_latest_used": synthetic_latest is not None,
        "run_dir": str(run_dir),
        "official_eval_complete": official_complete,
    }
    (run_dir / "official_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (run_dir / "selection.json").write_text(
        json.dumps(recommendation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if args.write_docs:
        DOCS_PATH.write_text(render_official_docs(summary), encoding="utf-8")
    print(f"Official benchmark complete: {run_dir}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PHASE 5C.2 official dataset benchmark")
    parser.add_argument("--dry-run-only", action="store_true", help="Validate dataset only")
    parser.add_argument("--require-ready", action="store_true", default=True)
    parser.add_argument("--no-require-ready", action="store_false", dest="require_ready")
    parser.add_argument("--write-docs", action="store_true")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--resume-dir", default=None)
    args = parser.parse_args()
    if args.dry_run_only:
        dry = run_official_dry_run()
        write_dry_run_artifacts(dry)
        ready = bool(dry.get("ready_for_official_benchmark"))
        print(f"READY_FOR_OFFICIAL_BENCHMARK={'TRUE' if ready else 'FALSE'}", flush=True)
        return 0 if ready else 2
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
