#!/usr/bin/env python3
"""Ingest official challenge clinical PDFs via existing knowledge lifecycle.

Resolves corpus root via LIMEN_DATASET_PATH → ./dataset/ → ./data/challenge/
(same order as evals.llm.official_dataset). Does not hard-code home paths.

Usage:
  export LIMEN_DATASET_PATH=/absolute/path/to/official/dataset
  make prepare-official-knowledge
  # or:
  LIMEN_RUNTIME_PROFILE=challenge python scripts/ingest_official_corpus.py --ingest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEXT_DIR_NAMES = ("textos", "texts", "pdfs", "documents")
SUPPORTED = {".pdf", ".txt", ".md", ".text"}
_PURGE_STATUSES = frozenset({"FAILED", "UPLOADED", "PROCESSING"})


def corpus_full_closed(
    *,
    discovered: int,
    indexed: int,
    duplicate: int,
    failed: int,
) -> bool:
    """True when every discovered file is AVAILABLE (new or already hashed)."""
    accounted = indexed + duplicate
    return bool(discovered) and accounted == discovered and failed == 0


def resolve_corpus_root() -> tuple[Path | None, str]:
    from evals.llm.official_dataset import canonical_resolution_candidates

    for label, path in canonical_resolution_candidates(ROOT):
        if path.is_dir():
            return path, label
        if path.is_file():
            return path.parent, label
    return None, "unavailable"


def discover_knowledge_files(corpus_root: Path) -> list[Path]:
    """Find clinical knowledge files under the resolved dataset root only."""
    candidates: list[Path] = []
    search_roots: list[Path] = [corpus_root]
    for name in TEXT_DIR_NAMES:
        nested = corpus_root / name
        if nested.is_dir():
            search_roots.append(nested)

    seen: set[Path] = set()
    for base in search_roots:
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            # Keep files under corpus_root only (no escape).
            try:
                resolved.relative_to(corpus_root.resolve())
            except ValueError:
                continue
            seen.add(resolved)
            candidates.append(resolved)
    return sorted(candidates, key=lambda p: str(p).lower())


def _apply_challenge_profile() -> None:
    if os.environ.get("LIMEN_RUNTIME_PROFILE", "").lower() != "challenge":
        os.environ.setdefault("LIMEN_RUNTIME_PROFILE", "challenge")
    from limen.config import settings as settings_module
    from limen.config.challenge_profile import apply_runtime_profile

    apply_runtime_profile()
    settings_module.get_settings.cache_clear()


def ingest_files(
    files: list[Path],
    *,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    from limen.auth import AuthService
    from limen.config.settings import get_settings
    from limen.knowledge.ingestion import DuplicateDocumentError, KnowledgeIngestionService
    from limen.knowledge.jobs import get_knowledge_job_runner, reset_knowledge_job_runner_for_tests
    from limen.persistence.database import get_database
    from limen.persistence.repositories import (
        SqliteAccountRepository,
        SqliteKnowledgeRepository,
    )

    selected = files if limit is None else files[:limit]
    report: dict[str, Any] = {
        "documents_discovered": len(files),
        "documents_selected": len(selected),
        "documents_indexed": 0,
        "documents_failed": 0,
        "documents_duplicate": 0,
        "pages_ocr": 0,
        "chunks_produced": 0,
        "failures": [],
        "purge_errors": [],
        "duplicates": [],
        "duration_s": None,
        "dry_run": dry_run,
    }
    if dry_run:
        report["sample"] = [str(p) for p in selected[:10]]
        return report

    settings = get_settings()
    settings.ensure_runtime_dirs()
    db = get_database(settings)
    db.initialize()
    if not settings.has_demo_account():
        report["error"] = "no_demo_account"
        report["hint"] = "Set LIMEN_DEMO_EMAIL / LIMEN_DEMO_PASSWORD"
        return report

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
    reset_knowledge_job_runner_for_tests()
    get_knowledge_job_runner()

    from limen.knowledge.deletion import KnowledgeDeletionService
    from limen.knowledge.embeddings import build_embedding_provider
    from limen.knowledge.vector_store import get_vector_store

    embeddings = build_embedding_provider(settings)
    vectors = get_vector_store(settings, dimensions=embeddings.dimensions)
    deletion = KnowledgeDeletionService(knowledge, vector_store=vectors)

    t0 = time.perf_counter()
    available_names: set[str] = set()
    for row in knowledge.list_documents(account.account_id):
        status = str(row.get("status") or "")
        name = str(row.get("source_name") or "")
        if status == "AVAILABLE":
            available_names.add(name)
            continue
        if status not in _PURGE_STATUSES:
            continue
        try:
            deletion.delete(account_id=account.account_id, document_id=row["document_id"])
        except Exception as exc:  # noqa: BLE001
            report["purge_errors"].append(
                {
                    "file": name,
                    "document_id": row.get("document_id"),
                    "error": f"purge:{type(exc).__name__}:{exc}",
                }
            )

    pending = [path for path in selected if path.name not in available_names]
    already = [path for path in selected if path.name in available_names]
    report["documents_duplicate"] += len(already)
    for path in already:
        report["duplicates"].append({"file": str(path), "reason": "already_available"})

    for index, path in enumerate(pending, start=1):
        print(f"[{index}/{len(pending)}] {path.name}", file=sys.stderr, flush=True)
        try:
            payload = path.read_bytes()
            doc = service.accept_upload(
                account_id=account.account_id,
                filename=path.name,
                payload=payload,
            )
            processed = service.process_document(
                account_id=account.account_id,
                document_id=doc["document_id"],
            )
            status = (processed or doc).get("status")
            if status == "AVAILABLE":
                report["documents_indexed"] += 1
                report["chunks_produced"] += knowledge.count_active_chunks(
                    account.account_id, doc["document_id"]
                )
            else:
                report["documents_failed"] += 1
                report["failures"].append(
                    {
                        "file": str(path),
                        "document_id": doc.get("document_id"),
                        "status": status,
                    }
                )
        except DuplicateDocumentError as exc:
            report["documents_duplicate"] += 1
            report["duplicates"].append(
                {
                    "file": str(path),
                    "existing_document_id": exc.existing.get("document_id"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            report["documents_failed"] += 1
            report["failures"].append(
                {
                    "file": str(path),
                    "error": f"{type(exc).__name__}:{exc}",
                }
            )
    available_after = {
        str(row.get("source_name") or "")
        for row in knowledge.list_documents(account.account_id)
        if row.get("status") == "AVAILABLE"
    }
    corpus_names = {path.name for path in files}
    report["corpus_filenames_available"] = len(corpus_names & available_after)
    report["extra_available_not_in_corpus"] = sorted(available_after - corpus_names)
    report["duration_s"] = round(time.perf_counter() - t0, 2)
    report["account_id"] = account.account_id
    report["ingest_mode"] = "direct"
    return report


def retrieval_smoke(account_id: str) -> list[dict[str, Any]]:
    from limen.config.settings import get_settings
    from limen.knowledge.embeddings import build_embedding_provider
    from limen.knowledge.hybrid import HybridEvidenceRetriever
    from limen.knowledge.retrieval import KnowledgeRetrievalService
    from limen.knowledge.vector_store import get_vector_store
    from limen.persistence.database import get_database
    from limen.persistence.repositories import SqliteKnowledgeRepository

    settings = get_settings()
    db = get_database(settings)
    knowledge = SqliteKnowledgeRepository(db)
    embeddings = build_embedding_provider(settings)
    vectors = get_vector_store(settings, dimensions=embeddings.dimensions)
    retriever = HybridEvidenceRetriever(
        lexical=KnowledgeRetrievalService(knowledge),
        vectors=vectors,
        embeddings=embeddings,
    )
    probes = [
        ("exact_es", "apendicitis aguda complicaciones postoperatorias"),
        ("paraphrase_es", "después de la cirugía del apéndice qué signos de alarma vigilar"),
        ("en_source_es_query", "dolor en la herida tras apendicectomía"),
        ("no_evidence", "LIMEN_NO_EVIDENCE_FACT_ZZZ_9999_UNIQUE"),
    ]
    out: list[dict[str, Any]] = []
    for name, query in probes:
        chunks = retriever.retrieve(account_id=account_id, query=query, limit=3)
        out.append(
            {
                "probe": name,
                "query": query,
                "hit_count": len(chunks),
                "evidence": [
                    {
                        "document_id": c.document_id,
                        "chunk_id": c.chunk_id,
                        "source_name": c.source_name,
                        "page": c.page,
                        "score": c.score,
                    }
                    for c in chunks
                ],
            }
        )
    return out


def ingest_files_http(
    files: list[Path],
    *,
    base_url: str,
    limit: int | None = None,
) -> dict[str, Any]:
    import httpx

    from limen.config.settings import get_settings

    settings = get_settings()
    selected = files if limit is None else files[:limit]
    report: dict[str, Any] = {
        "documents_discovered": len(files),
        "documents_selected": len(selected),
        "documents_indexed": 0,
        "documents_failed": 0,
        "documents_duplicate": 0,
        "chunks_produced": 0,
        "failures": [],
        "duplicates": [],
        "duration_s": None,
        "via_http": base_url,
    }
    t0 = time.perf_counter()
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=180.0) as client:
        login = client.post(
            "/api/auth/login",
            json={"email": settings.demo_email, "password": settings.demo_password},
        )
        login.raise_for_status()
        listed = client.get("/api/knowledge/documents")
        listed.raise_for_status()
        existing = listed.json()
        for row in existing:
            status = row.get("status")
            if status not in {"FAILED", "UPLOADED", "PROCESSING"}:
                continue
            doc_id = row.get("document_id")
            if not doc_id:
                continue
            deleted = client.delete(f"/api/knowledge/documents/{doc_id}")
            if deleted.status_code >= 400:
                report["failures"].append(
                    {
                        "file": row.get("source_name"),
                        "document_id": doc_id,
                        "error": f"purge_http_{deleted.status_code}",
                    }
                )
        listed = client.get("/api/knowledge/documents")
        listed.raise_for_status()
        available_names = {
            str(row.get("filename") or row.get("source_name") or "")
            for row in listed.json()
            if row.get("status") == "AVAILABLE"
        }
        pending = [path for path in selected if path.name not in available_names]
        already = [path for path in selected if path.name in available_names]
        report["documents_duplicate"] += len(already)
        for path in already:
            report["duplicates"].append({"file": str(path), "reason": "already_available"})
        for index, path in enumerate(pending, start=1):
            print(f"[{index}/{len(pending)}] {path.name}", flush=True)
            with path.open("rb") as handle:
                uploaded = client.post(
                    "/api/knowledge/documents",
                    files={"file": (path.name, handle, "application/pdf")},
                )
            if uploaded.status_code == 409:
                report["documents_duplicate"] += 1
                report["duplicates"].append({"file": str(path), "reason": "content_hash"})
                continue
            if uploaded.status_code >= 400:
                report["documents_failed"] += 1
                report["failures"].append(
                    {
                        "file": str(path),
                        "error": f"http_{uploaded.status_code}:{uploaded.text[:300]}",
                    }
                )
                continue
            document = uploaded.json()
            document_id = document.get("document_id")
            status = document.get("status")
            for _ in range(300):
                detail = client.get(f"/api/knowledge/documents/{document_id}")
                if detail.status_code >= 400:
                    break
                payload = detail.json()
                status = payload.get("status")
                if status == "AVAILABLE":
                    report["documents_indexed"] += 1
                    report["chunks_produced"] += int(payload.get("chunk_count") or 0)
                    available_names.add(path.name)
                    break
                if status == "FAILED":
                    report["documents_failed"] += 1
                    report["failures"].append(
                        {
                            "file": str(path),
                            "document_id": document_id,
                            "status": status,
                            "error": payload.get("failure_message"),
                        }
                    )
                    break
                time.sleep(1)
            else:
                report["documents_failed"] += 1
                report["failures"].append(
                    {
                        "file": str(path),
                        "document_id": document_id,
                        "status": status,
                        "error": "processing_timeout",
                    }
                )
    report["duration_s"] = round(time.perf_counter() - t0, 2)
    return report


def retrieval_smoke_http(base_url: str) -> list[dict[str, Any]]:
    import httpx

    from limen.config.settings import get_settings

    settings = get_settings()
    probes = [
        ("exact_es", "apendicitis aguda complicaciones postoperatorias"),
        ("paraphrase_es", "después de la cirugía del apéndice qué signos de alarma vigilar"),
        ("en_source_es_query", "dolor en la herida tras apendicectomía"),
        ("no_evidence", "LIMEN_NO_EVIDENCE_FACT_ZZZ_9999_UNIQUE"),
    ]
    out: list[dict[str, Any]] = []
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=60.0) as client:
        login = client.post(
            "/api/auth/login",
            json={"email": settings.demo_email, "password": settings.demo_password},
        )
        login.raise_for_status()
        for name, query in probes:
            response = client.get("/api/knowledge/retrieval-probe", params={"query": query})
            response.raise_for_status()
            body = response.json()
            evidence = body.get("evidence") or body.get("chunks") or []
            out.append(
                {
                    "probe": name,
                    "query": query,
                    "hit_count": (
                        len(evidence) if isinstance(evidence, list) else body.get("hit_count")
                    ),
                }
            )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Ingest discovered PDFs into the demo account",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover only; do not write to the knowledge store",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on documents to ingest (smoke)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run hybrid retrieval probes after ingest",
    )
    parser.add_argument(
        "--write-docs",
        action="store_true",
        help="Write docs/OFFICIAL_CORPUS.generated.md",
    )
    parser.add_argument(
        "--via-http",
        default=None,
        metavar="BASE_URL",
        help="Ingest through a running API (use when Qdrant is locked by run-challenge)",
    )
    args = parser.parse_args()

    _apply_challenge_profile()
    root, label = resolve_corpus_root()
    if root is None:
        payload = {
            "ok": False,
            "error": "official_dataset_unavailable",
            "hint": (
                "export LIMEN_DATASET_PATH=/absolute/path/to/official/dataset "
                "(directory containing textos/ PDFs and/or xlsx files)"
            ),
        }
        print(json.dumps(payload, indent=2))
        return 1

    files = discover_knowledge_files(root)
    result: dict[str, Any] = {
        "ok": True,
        "corpus_root": str(root),
        "resolved_via": label,
        "documents_discovered": len(files),
    }

    if args.dry_run or not args.ingest:
        result["ingest"] = ingest_files(files, limit=args.limit, dry_run=True)
        if not args.ingest:
            result["note"] = "Pass --ingest to index into the demo account."
    elif args.via_http:
        result["ingest"] = ingest_files_http(
            files,
            base_url=args.via_http,
            limit=args.limit,
        )
        if args.smoke:
            result["retrieval_smoke"] = retrieval_smoke_http(args.via_http)
    else:
        result["ingest"] = ingest_files(files, limit=args.limit, dry_run=False)
        account_id = result["ingest"].get("account_id")
        if args.smoke and isinstance(account_id, str):
            result["retrieval_smoke"] = retrieval_smoke(account_id)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.write_docs:
        _write_docs(result)
    failed = int((result.get("ingest") or {}).get("documents_failed") or 0)
    if args.ingest and failed:
        return 2
    return 0


def _write_docs(result: dict[str, Any]) -> None:
    docs = ROOT / "docs" / "OFFICIAL_CORPUS.generated.md"
    ingest = result.get("ingest") or {}
    discovered = int(result.get("documents_discovered") or 0)
    indexed = int(ingest.get("documents_indexed") or 0)
    duplicate = int(ingest.get("documents_duplicate") or 0)
    failed = int(ingest.get("documents_failed") or 0)
    accounted = indexed + duplicate
    full_closed = corpus_full_closed(
        discovered=discovered,
        indexed=indexed,
        duplicate=duplicate,
        failed=failed,
    )
    result["corpus_accounted"] = accounted
    result["full_corpus_closed"] = full_closed
    matching = ingest.get("corpus_filenames_available")
    extra = ingest.get("extra_available_not_in_corpus") or []
    lines = [
        "# Official Corpus Preparation (generated)",
        "",
        f"Corpus root: `{result.get('corpus_root')}`",
        f"Resolved via: `{result.get('resolved_via')}`",
        f"Ingest mode: `{ingest.get('ingest_mode') or ingest.get('via_http') or 'unknown'}`",
        f"Documents discovered: **{result.get('documents_discovered')}**",
        f"Indexed (new AVAILABLE this run): **{ingest.get('documents_indexed')}**",
        f"Failed: **{ingest.get('documents_failed')}**",
        f"Duplicates (already AVAILABLE / content-hash): **{ingest.get('documents_duplicate')}**",
        f"Accounted (indexed + duplicate): **{accounted} / {discovered}**",
        f"Corpus filenames AVAILABLE: **"
        f"{matching if matching is not None else 'n/a'} / {discovered}**",
        f"Full corpus closed: **{'yes' if full_closed else 'no'}**",
        f"Chunks produced: **{ingest.get('chunks_produced')}**",
        f"Duration (s): **{ingest.get('duration_s')}**",
        "",
        "## Extra AVAILABLE (not in official corpus)",
        "",
    ]
    if extra:
        for name in extra:
            lines.append(f"- `{name}`")
    else:
        lines.append("_None, or not counted in this mode._")
    lines.extend(
        [
            "",
            "## Retrieval smoke",
            "",
        ]
    )
    smoke = result.get("retrieval_smoke") or []
    if not smoke:
        lines.append("_Not run (pass `--smoke`)._")
    for row in smoke:
        lines.append(f"- `{row['probe']}`: hits={row['hit_count']} query={row['query']!r}")
    lines.append("")
    docs.write_text("\n".join(lines), encoding="utf-8")
    out_json = ROOT / "runtime" / "evals" / "corpus" / "latest.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {docs}")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    raise SystemExit(main())
