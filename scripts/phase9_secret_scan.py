#!/usr/bin/env python3
"""Repository hygiene / secret scan for PHASE 9 (read-only report)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUSPICIOUS_NAME = re.compile(
    r"(\.env$|\.pem$|credentials|secret|api[_-]?key|\.sqlite$|\.db$|"
    r"model\.safetensors|\.onnx$|node_modules|\.venv)",
    re.I,
)
# Avoid matching .env.example
ALLOW_NAMES = {".env.example"}


def main() -> int:
    tracked = subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True
    ).splitlines()
    findings: list[dict[str, str]] = []
    for rel in tracked:
        name = Path(rel).name
        if name in ALLOW_NAMES:
            continue
        if SUSPICIOUS_NAME.search(rel) or SUSPICIOUS_NAME.search(name):
            findings.append({"path": rel, "reason": "suspicious_tracked_name"})

    # Untracked runtime artefacts that must stay gitignored
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    required_ignores = [
        ".env",
        ".venv/",
        "node_modules/",
        "runtime/",
        "*.db",
        ".cache/",
    ]
    missing_ignore = [p for p in required_ignores if p not in gitignore]

    report = {
        "tracked_suspicious": findings,
        "missing_gitignore_patterns": missing_ignore,
        "ok": not findings and not missing_ignore,
    }
    out = ROOT / "runtime" / "evals" / "phase9_secret_scan.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
