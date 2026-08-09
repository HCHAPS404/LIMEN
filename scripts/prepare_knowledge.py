#!/usr/bin/env python3
"""Deterministic knowledge bootstrap for challenge runtime.

Does NOT ingest the full official PDF corpus on every launch.

Creates/ensures a small reproducible seed document under
``runtime/knowledge_seed/`` and optionally ingests it for the demo account
when ``--ingest`` is passed and credentials exist.

Usage:
  make prepare-knowledge
  make prepare-knowledge INGEST=1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEED_DIR = ROOT / "runtime" / "knowledge_seed"
SEED_NAME = "limen_seed_postop_es.md"
SEED_MARKER = "LIMEN_SEED_FACT_UMBRAL_404"
SEED_BODY = f"""# Guía seed LIMEN (corpus inicial reproducible)

Documento de arranque determinista. No sustituye el corpus oficial completo.

## Hecho único de verificación

{SEED_MARKER}: tras una apendicectomía sin complicaciones, el seguimiento
teleasistencia debe preguntar por fiebre, enrojecimiento de herida y dolor
progresivo en las primeras 72 horas.

## Observación esperada

Si el paciente niega fiebre y describe dolor leve estable, el riesgo suele
mantenerse en observación (GREEN/YELLOW según Safety Governor). Signos de
urgencia respiratoria o sangrado activo requieren escalamiento.

## Provenance

source=limen_seed_postop_es.md
version=1
"""


def write_seed() -> Path:
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    path = SEED_DIR / SEED_NAME
    path.write_text(SEED_BODY, encoding="utf-8")
    meta = {
        "filename": SEED_NAME,
        "marker": SEED_MARKER,
        "path": str(path),
        "bytes": path.stat().st_size,
        "note": (
            "Full official corpus ingestion remains opt-in / Planned. "
            "Use admin console for live G5 uploads."
        ),
    }
    (SEED_DIR / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return path


def ingest_for_demo(path: Path) -> dict[str, object]:
    from limen.auth import AuthService
    from limen.config.settings import get_settings
    from limen.knowledge.ingestion import KnowledgeIngestionService
    from limen.knowledge.jobs import get_knowledge_job_runner, reset_knowledge_job_runner_for_tests
    from limen.persistence.database import get_database
    from limen.persistence.repositories import (
        SqliteAccountRepository,
        SqliteKnowledgeRepository,
    )

    settings = get_settings()
    settings.ensure_runtime_dirs()
    db = get_database(settings)
    db.initialize()
    if not settings.has_demo_account():
        return {
            "ingested": False,
            "reason": "no_demo_account",
            "hint": "Set LIMEN_DEMO_EMAIL / LIMEN_DEMO_PASSWORD",
        }
    auth = AuthService(
        SqliteAccountRepository(db),
        session_ttl=settings.auth_session_ttl(),
    )
    account = auth.ensure_account(
        settings.demo_email,
        settings.demo_password,
        settings.demo_display_name,
    )
    knowledge = SqliteKnowledgeRepository(db)
    service = KnowledgeIngestionService(knowledge, settings)
    payload = path.read_bytes()
    try:
        doc = service.accept_upload(
            account_id=account.account_id,
            filename=path.name,
            payload=payload,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ingested": False, "error": f"{type(exc).__name__}:{exc}"}

    # Process synchronously for bootstrap determinism.
    processed = service.process_document(
        account_id=account.account_id,
        document_id=doc["document_id"],
    )
    reset_knowledge_job_runner_for_tests()
    get_knowledge_job_runner()
    return {
        "ingested": True,
        "document_id": doc["document_id"],
        "status": (processed or doc).get("status"),
        "account_id": account.account_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Also ingest seed into demo account (requires demo credentials)",
    )
    args = parser.parse_args()
    # Optional challenge profile for real embeddings on ingest.
    if os.environ.get("LIMEN_RUNTIME_PROFILE", "").lower() == "challenge":
        from limen.config import settings as settings_module
        from limen.config.challenge_profile import apply_runtime_profile

        apply_runtime_profile()
        settings_module.get_settings.cache_clear()

    path = write_seed()
    result: dict[str, object] = {
        "seed_path": str(path),
        "marker": SEED_MARKER,
        "prepare": "ok",
    }
    if args.ingest:
        result["ingest"] = ingest_for_demo(path)
    print(json.dumps(result, indent=2))
    print(
        "Knowledge seed ready. Official PDFs: "
        "LIMEN_DATASET_PATH=... make prepare-official-knowledge"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
