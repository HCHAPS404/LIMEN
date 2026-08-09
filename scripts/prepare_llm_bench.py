#!/usr/bin/env python3
"""Opt-in G3 model acquisition for LLM benchmarks.

Never pulls unrelated models. Never uses sudo.
Normal bootstrap does NOT call this.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.llm.preflight import G3_LOCAL_CANDIDATES, print_preflight, run_preflight


def _pull(model: str) -> int:
    print(f"Pulling G3 candidate: {model}")
    proc = subprocess.run(["ollama", "pull", model], check=False)
    return int(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Explicitly download missing G3 candidates via ollama pull",
    )
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    report = run_preflight(base_url=args.base_url)
    print_preflight(report)

    missing = [c.candidate_id for c in report.candidates if not c.installed]
    if not missing:
        print("All G3 local candidates already installed.")
        return 0 if report.ready_for_benchmark else 2

    print("Missing G3 candidates:")
    for mid in missing:
        print(f"  - {mid}")
        print(f"    required: ollama pull {mid}")

    if not args.pull:
        print(
            "Refusing to download multi-GB models without --pull "
            "(or: make prepare-llm-bench PULL=1)."
        )
        return 2

    if not report.binary_ok:
        print("Cannot pull: ollama binary missing.")
        return 2
    if not report.server_ok:
        print("Cannot pull: Ollama server unreachable.")
        return 2

    rc = 0
    for mid in missing:
        if mid not in G3_LOCAL_CANDIDATES:
            print(f"Refusing non-G3 model: {mid}")
            rc = 2
            continue
        pull_rc = _pull(mid)
        if pull_rc != 0:
            print(f"pull failed for {mid} (exit {pull_rc})")
            rc = pull_rc or 2

    print("Re-running preflight after pull…")
    final = run_preflight(base_url=args.base_url)
    print_preflight(final)
    return (
        0
        if final.ready_for_benchmark and not any(not c.installed for c in final.candidates)
        else (rc or 2)
    )


if __name__ == "__main__":
    raise SystemExit(main())
