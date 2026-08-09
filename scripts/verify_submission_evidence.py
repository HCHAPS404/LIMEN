#!/usr/bin/env python3
"""Scan submission-facing docs for FINAL_EVIDENCE_REQUIRED markers.

Does not fail ordinary CI. Exit 0 always unless --strict is passed.
With --strict, exit 1 if any markers remain (final submission mode).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = re.compile(r"FINAL_EVIDENCE_REQUIRED:([A-Z0-9_]+)")

SCAN_GLOBS = (
    "README.md",
    "docs/submission/**/*.md",
    "docs/FINAL_POLISH_REGISTER.md",
    "docs/CHALLENGE_RUNTIME.md",
    "docs/deliverables/**/*.md",
)


def collect() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for pattern in SCAN_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in MARKER.finditer(text):
                token = match.group(1)
                found.setdefault(token, []).append(
                    f"{path.relative_to(ROOT)}:{text[: match.start()].count(chr(10)) + 1}"
                )
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any FINAL_EVIDENCE_REQUIRED markers remain",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    found = collect()
    tokens = sorted(found)
    report = {
        "unresolved_count": len(tokens),
        "tokens": tokens,
        "locations": found,
        "strict": args.strict,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"FINAL_EVIDENCE_REQUIRED unresolved: {len(tokens)}")
        for token in tokens:
            locs = ", ".join(found[token][:5])
            more = "" if len(found[token]) <= 5 else f" (+{len(found[token]) - 5})"
            print(f"  - {token}: {locs}{more}")
        if not tokens:
            print("  (none)")

    out = ROOT / "runtime" / "evals" / "submission_evidence_scan.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.strict and tokens:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
