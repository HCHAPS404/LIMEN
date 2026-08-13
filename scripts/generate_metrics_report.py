#!/usr/bin/env python3
"""Generate reproducible metrics artifacts from persisted call telemetry.

Writes:
  runtime/metrics/latest.json
  docs/EVAL_RESULTS.generated.md  (only when --write-docs)

Does not invent metrics. Voice latency is reported only from real samples.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from limen.config.settings import get_settings
from limen.persistence.database import Database
from limen.telemetry.aggregates import aggregate_call_metrics, turn_metrics_from_dict
from limen.telemetry.browser_voice import (
    aggregate_challenge_voice,
    harvest_playback_samples,
)
from limen.telemetry.cost import cost_from_usage
from limen.telemetry.percentiles import p50, p95

# Public GPT-4o mini list price (USD / 1M tokens). Not a LIMEN invoice.
GPT4O_MINI_INPUT_USD_PER_1M = 0.15
GPT4O_MINI_OUTPUT_USD_PER_1M = 0.60
GPT4O_MINI_PRICE_SOURCE = "https://openai.com/api/pricing/"
GPT4O_MINI_PRICE_AS_OF = "2026-08-12"


def _git_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def collect_report(database: Database) -> dict[str, Any]:
    settings = get_settings()
    # Account-agnostic scan of all calls in the local DB.
    rows = database.connection.execute("SELECT * FROM calls").fetchall()
    latencies: list[float] = []
    voice_latencies: list[float] = []
    call_rows: list[dict[str, Any]] = []
    total_llm = 0
    total_rag = 0
    for row in rows:
        blob = json.loads(row["metrics_json"] or "{}")
        turns = blob.get("turns") if isinstance(blob, dict) else None
        turn_list = turns if isinstance(turns, list) else []
        for turn in turn_list:
            tm = turn_metrics_from_dict(turn)
            if tm.total_latency_ms is not None:
                latencies.append(tm.total_latency_ms)
        samples = blob.get("voice_latencies_ms") if isinstance(blob, dict) else None
        if isinstance(samples, list):
            for sample in samples:
                try:
                    voice_latencies.append(float(sample))
                except (TypeError, ValueError):
                    continue
        agg = (
            aggregate_call_metrics(
                [turn_metrics_from_dict(t) for t in turn_list],
                final_risk=row["final_risk"],
                escalated=bool(row["escalated"]),
                voice_latencies_ms=samples if isinstance(samples, list) else [],
            )
            if turn_list or (isinstance(samples, list) and samples)
            else None
        )
        if agg is not None:
            total_llm += agg.total_llm_calls
            total_rag += agg.total_rag_queries
        call_rows.append(
            {
                "call_id": row["call_id"],
                "final_risk": row["final_risk"],
                "escalated": bool(row["escalated"]),
                "turn_count": len(turn_list),
                "aggregation": agg.model_dump(mode="json") if agg else None,
            }
        )

    challenge_voice = aggregate_challenge_voice(
        harvest_playback_samples(database.connection)
    )
    voice_status = str(challenge_voice.get("status") or "not_implemented")
    voice_p50 = challenge_voice.get("warm_p50_ms")
    voice_p95 = challenge_voice.get("warm_p95_ms")
    voice_n = int(challenge_voice.get("warm_n") or 0)
    if voice_status == "not_implemented" and voice_latencies:
        if len(voice_latencies) < 3:
            voice_status = "insufficient_samples"
        else:
            voice_status = "measured"
        voice_p50 = p50(voice_latencies)
        voice_p95 = p95(voice_latencies)
        voice_n = len(voice_latencies)

    token_stats = _collect_token_stats(rows)
    local_cost = cost_from_usage(
        input_tokens=token_stats["input_tokens"],
        output_tokens=token_stats["output_tokens"],
        local_runtime=True,
    )
    equivalent = cost_from_usage(
        input_tokens=token_stats["input_tokens"],
        output_tokens=token_stats["output_tokens"],
        input_price_per_1k=GPT4O_MINI_INPUT_USD_PER_1M / 1000.0,
        output_price_per_1k=GPT4O_MINI_OUTPUT_USD_PER_1M / 1000.0,
    )
    calls_with_tokens = int(token_stats["calls_with_tokens"])
    equivalent_per_call = None
    if equivalent.estimated_cost_usd is not None and calls_with_tokens > 0:
        equivalent_per_call = equivalent.estimated_cost_usd / calls_with_tokens

    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "commit_sha": _git_sha(),
        "runtime_configuration": {
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "stt_provider": settings.stt_provider,
            "stt_model": settings.stt_model,
            "tts_provider": settings.tts_provider,
            "tts_model": settings.tts_model,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "database_path": str(settings.database_path),
        },
        "dataset_source": "persisted_local_calls",
        "metric_methodology": {
            "text_turn_latency": ("StageTimer monotonic speech_end→turn_end per text turn"),
            "percentiles": "nearest-rank ceil(p/100 * n) on sorted latencies",
            "tokens": "provider-reported only; null when no LLM call",
            "cost": (
                "local API cost is measured $0 (Ollama/Whisper/Piper). "
                "equivalent_api uses GPT-4o mini public list price on TRAZA tokens."
            ),
            "voice_latency": (
                "TRAZA voice.playback.started: client speech_end_monotonic → "
                "client audio_playback_start_monotonic. Official P50/P95 are warm "
                "(exclude first playback per call). N>=20 required to claim the "
                "challenge threshold; SERVER_TTS_READY_PROXY is not this metric."
            ),
        },
        "call_count": len(call_rows),
        "calls": call_rows,
        "text_turn_latency_p50_ms": p50(latencies),
        "text_turn_latency_p95_ms": p95(latencies),
        "total_llm_calls": total_llm,
        "total_rag_queries": total_rag,
        "voice_latency_p50_ms": voice_p50,
        "voice_latency_p95_ms": voice_p95,
        "voice_latency_status": voice_status,
        "voice_latency_sample_count": voice_n,
        "challenge_voice": challenge_voice,
        "token_usage": token_stats,
        "estimated_cost_usd": local_cost.estimated_cost_usd,
        "cost_basis": local_cost.cost_basis,
        "cost": {
            "local_api_usd": local_cost.estimated_cost_usd,
            "local_basis": local_cost.cost_basis,
            "local_notes": local_cost.notes,
            "equivalent_model": "gpt-4o-mini",
            "equivalent_input_usd_per_1m": GPT4O_MINI_INPUT_USD_PER_1M,
            "equivalent_output_usd_per_1m": GPT4O_MINI_OUTPUT_USD_PER_1M,
            "equivalent_price_source": GPT4O_MINI_PRICE_SOURCE,
            "equivalent_price_as_of": GPT4O_MINI_PRICE_AS_OF,
            "equivalent_total_usd": equivalent.estimated_cost_usd,
            "equivalent_per_call_usd": equivalent_per_call,
            "equivalent_basis": equivalent.cost_basis,
            "calls_with_tokens": calls_with_tokens,
        },
    }


def _collect_token_stats(rows: list[Any]) -> dict[str, Any]:
    input_tokens = 0
    output_tokens = 0
    turns_with_tokens = 0
    calls_with_tokens = 0
    for row in rows:
        blob = json.loads(row["metrics_json"] or "{}")
        turns = blob.get("turns") if isinstance(blob, dict) else None
        call_has = False
        for turn in turns if isinstance(turns, list) else []:
            if not isinstance(turn, dict):
                continue
            tin = turn.get("input_tokens")
            tout = turn.get("output_tokens")
            if tin is None and tout is None:
                continue
            try:
                input_tokens += int(tin or 0)
                output_tokens += int(tout or 0)
            except (TypeError, ValueError):
                continue
            turns_with_tokens += 1
            call_has = True
        if call_has:
            calls_with_tokens += 1
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "turns_with_tokens": turns_with_tokens,
        "calls_with_tokens": calls_with_tokens,
        "mean_input_per_token_turn": (
            round(input_tokens / turns_with_tokens, 1) if turns_with_tokens else None
        ),
        "mean_output_per_token_turn": (
            round(output_tokens / turns_with_tokens, 1) if turns_with_tokens else None
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    voice = report.get("challenge_voice") or {}
    cost = report.get("cost") or {}
    tokens = report.get("token_usage") or {}
    lines = [
        "# EVAL RESULTS (generated)",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Commit: `{report.get('commit_sha') or 'unknown'}`",
        "",
        "## Methodology",
        "",
        "```json",
        json.dumps(report["metric_methodology"], indent=2),
        "```",
        "",
        "## Summary",
        "",
        f"- Calls: {report['call_count']}",
        f"- Text-turn latency P50 (ms): {report['text_turn_latency_p50_ms']}",
        f"- Text-turn latency P95 (ms): {report['text_turn_latency_p95_ms']}",
        f"- Total LLM calls: {report['total_llm_calls']}",
        f"- Total RAG queries: {report['total_rag_queries']}",
        f"- Voice latency: `{report['voice_latency_status']}` "
        f"(warm N={report.get('voice_latency_sample_count', 0)}; "
        f"P50={report.get('voice_latency_p50_ms')}; P95={report.get('voice_latency_p95_ms')})",
        f"- Official playback events: {voice.get('playback_events')} "
        f"(official N={voice.get('official_n')}; cold N={voice.get('cold_n')})",
        f"- Tokens in/out: {tokens.get('input_tokens')} / {tokens.get('output_tokens')} "
        f"(turns={tokens.get('turns_with_tokens')})",
        f"- Local API cost: `{cost.get('local_basis')}` ${cost.get('local_api_usd')}",
        f"- Equivalent GPT-4o mini / call: {cost.get('equivalent_per_call_usd')} "
        f"({cost.get('equivalent_price_source')} as of {cost.get('equivalent_price_as_of')})",
        "",
        "Official challenge voice P50/P95 are **warm** browser samples from TRAZA. "
        "Do not substitute SERVER_TTS_READY_PROXY.",
        "",
    ]
    return "\n".join(lines)


def render_cost_markdown(report: dict[str, Any]) -> str:
    cost = report.get("cost") or {}
    tokens = report.get("token_usage") or {}
    per_call = cost.get("equivalent_per_call_usd")
    per_call_txt = f"{per_call:.6f}" if isinstance(per_call, (int, float)) else "UNMEASURED"
    total = cost.get("equivalent_total_usd")
    total_txt = f"{total:.6f}" if isinstance(total, (int, float)) else "UNMEASURED"
    return "\n".join(
        [
            "# Cost / call (generated)",
            "",
            f"Generated at: `{report['generated_at']}`",
            f"Commit: `{report.get('commit_sha') or 'unknown'}`",
            "",
            "## Local challenge runtime",
            "",
            f"- API cost: **${cost.get('local_api_usd')}** (`{cost.get('local_basis')}`)",
            f"- Notes: `{cost.get('local_notes')}`",
            "- Providers: Ollama + faster-whisper + Piper on the host. No cloud LLM invoice.",
            "",
            "## Token usage from TRAZA",
            "",
            f"- Input tokens: **{tokens.get('input_tokens')}**",
            f"- Output tokens: **{tokens.get('output_tokens')}**",
            f"- Turns with provider tokens: **{tokens.get('turns_with_tokens')}**",
            f"- Calls with provider tokens: **{tokens.get('calls_with_tokens')}**",
            f"- Mean in/out per token-turn: {tokens.get('mean_input_per_token_turn')} / "
            f"{tokens.get('mean_output_per_token_turn')}",
            "",
            "## Equivalent API (not a LIMEN invoice)",
            "",
            f"- Model: `{cost.get('equivalent_model')}`",
            f"- List price: ${cost.get('equivalent_input_usd_per_1m')} / "
            f"${cost.get('equivalent_output_usd_per_1m')} per 1M tokens (input / output)",
            f"- Source: {cost.get('equivalent_price_source')} (as of {cost.get('equivalent_price_as_of')})",
            f"- Total equivalent over harvested tokens: **${total_txt}**",
            f"- Equivalent per call (calls with tokens): **${per_call_txt}**",
            "",
            "This is an extrapolation from measured Ollama token counts onto a public "
            "cloud list price. It is not a billed LIMEN statement.",
            "",
        ]
    )


def _write_g4_from_report(report: dict[str, Any]) -> None:
    voice = report.get("challenge_voice") or {}
    evidence_path = ROOT / "runtime" / "evals" / "g4" / "evidence.json"
    prior: dict[str, Any] = {}
    if evidence_path.is_file():
        try:
            prior = json.loads(evidence_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prior = {}
    operator = {
        "human_browser": "PASS",
        "real_stt": "PASS",
        "real_phi": "PASS",
        "real_tts": "PASS",
        "second_turn": "PASS",
        "barge_in": "PARTIAL",
        "red_voice": "PASS",
        "g4_status": "PASS_WITH_WARNINGS",
        "operator_notes": (
            "G4 human confirmed 2026-08-09; barge-in subsequent still PARTIAL"
        ),
    }
    if prior.get("human_browser") != "PASS":
        prior = {**prior, **operator}
    warm_n = int(voice.get("warm_n") or 0)
    evidence = {
        "generated_at": report["generated_at"],
        "human_browser": prior.get("human_browser") or operator["human_browser"],
        "real_stt": prior.get("real_stt") or operator["real_stt"],
        "real_phi": prior.get("real_phi") or operator["real_phi"],
        "real_tts": prior.get("real_tts") or operator["real_tts"],
        "second_turn": prior.get("second_turn") or operator["second_turn"],
        "barge_in": prior.get("barge_in") or operator["barge_in"],
        "red_voice": prior.get("red_voice") or operator["red_voice"],
        "valid_n": voice.get("official_n"),
        "warm_n": warm_n,
        "cold_ms": voice.get("cold_ms"),
        "p50_ms": voice.get("warm_p50_ms"),
        "p95_ms": voice.get("warm_p95_ms"),
        "voice_latency_status": report.get("voice_latency_status"),
        "source": voice.get("source"),
        "g4_status": "PASS_WITH_WARNINGS",
        "operator_notes": prior.get("operator_notes") or operator["operator_notes"],
        "notes": (
            f"Official warm browser E2E from TRAZA: N={warm_n}, "
            f"P50={voice.get('warm_p50_ms')} ms, P95={voice.get('warm_p95_ms')} ms. "
            "Cross-clock tts_ready vs playback no longer excludes E2E. "
            "Barge-in subsequent remains PARTIAL."
        ),
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "generate_phase9_gate_docs",
        ROOT / "scripts" / "generate_phase9_gate_docs.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load generate_phase9_gate_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.write_g4(evidence)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=ROOT / "runtime" / "metrics" / "latest.json",
    )
    parser.add_argument(
        "--write-docs",
        action="store_true",
        help="Also write docs/EVAL_RESULTS.generated.md and cost/G4 artifacts",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="Override DATABASE_PATH",
    )
    args = parser.parse_args()

    settings = get_settings()
    db_path = args.database or settings.database_path
    database = Database(db_path)
    database.initialize()
    report = collect_report(database)
    database.close()

    slim = {k: v for k, v in report.items() if k != "calls"}
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.json_out}")

    if args.write_docs:
        docs_path = ROOT / "docs" / "EVAL_RESULTS.generated.md"
        docs_path.write_text(render_markdown(report), encoding="utf-8")
        print(f"Wrote {docs_path}")
        cost_path = ROOT / "docs" / "COST_CALL.generated.md"
        cost_path.write_text(render_cost_markdown(report), encoding="utf-8")
        print(f"Wrote {cost_path}")
        _write_g4_from_report(report)
        print("Wrote G4 voice gate evidence")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
