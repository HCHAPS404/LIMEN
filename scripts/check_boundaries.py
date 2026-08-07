#!/usr/bin/env python3
"""Fail if vendor SDK imports appear outside allowed adapter paths."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_MODULES = (
    "openai",
    "anthropic",
    "groq",
    "together",
    "cohere",
    "google.generativeai",
    "vertexai",
    "langchain",
    "llama_index",
    "llama_cpp",
)

ALLOWED_PREFIXES = (
    "limen/intelligence/providers/",
    "limen/voice/",  # future STT/TTS adapters
    "limen/knowledge/embeddings.py",
)

IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+(" + "|".join(re.escape(m) for m in FORBIDDEN_MODULES) + r")\b"
)


def is_allowed(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(rel.startswith(prefix.rstrip("/")) or rel == prefix for prefix in ALLOWED_PREFIXES)


def main() -> int:
    violations: list[str] = []
    scan_roots = [ROOT / "limen", ROOT / "apps" / "api", ROOT / "scripts", ROOT / "evals"]
    for root in scan_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if is_allowed(path):
                continue
            text = path.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), start=1):
                if IMPORT_RE.search(line):
                    violations.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")

    if violations:
        print("Boundary check FAILED — vendor SDK imports outside adapters:")
        for item in violations:
            print(f"  {item}")
        return 1

    print("Boundary check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
