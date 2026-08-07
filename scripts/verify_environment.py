#!/usr/bin/env python3
"""Verify local environment for LIMEN foundation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from limen.config.settings import get_settings
from limen.intelligence.providers import build_llm_provider
from limen.knowledge.embeddings import build_embedding_provider
from limen.persistence.database import Database
from limen.voice.stt import build_stt_provider
from limen.voice.tts import build_tts_provider


def main() -> int:
    settings = get_settings()
    settings.ensure_runtime_dirs()
    errors: list[str] = []

    try:
        build_llm_provider(settings)
        build_stt_provider(settings)
        build_tts_provider(settings)
        build_embedding_provider(settings)
    except ValueError as exc:
        errors.append(str(exc))

    db = Database(settings.database_path)
    db.initialize()
    health = db.health()
    db.close()
    if health.get("database") != "ok":
        errors.append("database health failed")

    required = [
        ROOT / "ARCHITECTURE.md",
        ROOT / "AGENTS.md",
        ROOT / "apps" / "api" / "main.py",
        ROOT / "apps" / "web" / "package.json",
        ROOT / "BACKEND.md",
        ROOT / "FRONTEND.md",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")

    if errors:
        print("Environment verification FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("Environment verification OK")
    print(f"  LLM: {settings.llm_provider}/{settings.llm_model}")
    print(f"  DB:  {settings.database_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
