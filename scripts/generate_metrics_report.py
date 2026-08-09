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
from limen.telemetry.percentiles import p50, p95


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

    if not voice_latencies:
        voice_status = "not_implemented"
        voice_p50 = None
        voice_p95 = None
    elif len(voice_latencies) < 3:
        voice_status = "insufficient_samples"
        voice_p50 = p50(voice_latencies)
        voice_p95 = p95(voice_latencies)
    else:
        voice_status = "measured"
        voice_p50 = p50(voice_latencies)
        voice_p95 = p95(voice_latencies)

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
            "cost": "not_available unless pricing configured",
            "voice_latency": (
                "client speech_end_monotonic → agent_audio_started_monotonic; "
                "UNMEASURED until real voice samples exist"
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
        "voice_latency_sample_count": len(voice_latencies),
        "estimated_cost_usd": None,
        "cost_basis": "not_available",
    }


def render_markdown(report: dict[str, Any]) -> str:
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
        f"(samples={report.get('voice_latency_sample_count', 0)}; "
        f"P50={report.get('voice_latency_p50_ms')}; P95={report.get('voice_latency_p95_ms')})",
        f"- Cost basis: `{report['cost_basis']}`",
        "",
        "This file is machine-generated. Do not treat it as challenge voice scores.",
        "",
    ]
    return "\n".join(lines)


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
        help="Also write docs/EVAL_RESULTS.generated.md",
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

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.json_out}")

    if args.write_docs:
        docs_path = ROOT / "docs" / "EVAL_RESULTS.generated.md"
        docs_path.write_text(render_markdown(report), encoding="utf-8")
        print(f"Wrote {docs_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
