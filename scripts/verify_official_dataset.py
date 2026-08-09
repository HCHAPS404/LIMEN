#!/usr/bin/env python3
"""Dry-run validation for official Tech Sphere dataset (PHASE 5C.2).

No LLM calls. Writes fingerprint + discovery JSON under runtime/benchmarks/llm/.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.llm.official_benchmark import run_official_dry_run, write_dry_run_artifacts


def main() -> int:
    report = run_official_dry_run()
    write_dry_run_artifacts(report)
    ready = bool(report.get("ready_for_official_benchmark"))
    print(f"READY_FOR_OFFICIAL_BENCHMARK={'TRUE' if ready else 'FALSE'}", flush=True)
    if not ready:
        for err in report.get("validation_errors") or []:
            print(f"  - {err}", flush=True)
        return 2
    stats = report.get("reconstruction_stats") or {}
    print(
        f"Conversations: {stats.get('conversation_count')} | "
        f"Turns: {stats.get('turn_count')} | "
        f"Labels: {stats.get('label_distribution_by_case')}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
