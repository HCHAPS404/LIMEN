#!/usr/bin/env python3
"""Knowledge lifecycle with stub or real embedding provider."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from limen.auth import AuthService
from limen.config.settings import ApplicationSettings
from limen.knowledge.deletion import KnowledgeDeletionService
from limen.knowledge.embeddings import build_embedding_provider
from limen.knowledge.hybrid import HybridEvidenceRetriever
from limen.knowledge.ingestion import KnowledgeIngestionService
from limen.knowledge.retrieval import KnowledgeRetrievalService
from limen.knowledge.vector_store import get_vector_store, reset_vector_store_for_tests
from limen.persistence.database import Database
from limen.persistence.repositories.accounts import SqliteAccountRepository
from limen.persistence.repositories.knowledge import SqliteKnowledgeRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("stub", "real"), default="stub")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if args.provider == "stub":
            settings = ApplicationSettings(
                DATABASE_PATH=root / "eval.db",
                DOCUMENT_PATH=root / "documents",
                VECTOR_PATH=root / "vectors",
                EMBEDDING_PROVIDER="stub",
                VECTOR_STORE_BACKEND="qdrant",
                LLM_PROVIDER="stub",
                _env_file=None,
            )
        else:
            import os

            path = os.environ.get("EMBEDDING_MODEL_PATH", "").strip()
            kwargs: dict = {
                "DATABASE_PATH": root / "eval.db",
                "DOCUMENT_PATH": root / "documents",
                "VECTOR_PATH": root / "vectors",
                "EMBEDDING_PROVIDER": "sentence-transformers",
                "EMBEDDING_MODEL": "intfloat/multilingual-e5-small",
                "VECTOR_STORE_BACKEND": "qdrant",
                "LLM_PROVIDER": "stub",
                "_env_file": None,
            }
            if path:
                kwargs["EMBEDDING_MODEL_PATH"] = path
            settings = ApplicationSettings(**kwargs)
        settings.ensure_runtime_dirs()
        reset_vector_store_for_tests()
        database = Database(settings.database_path)
        database.initialize()
        auth = AuthService(SqliteAccountRepository(database))
        account = auth.register("eval@limen.local", "eval-password-2026", "Eval").account
        knowledge = SqliteKnowledgeRepository(database)
        emb = build_embedding_provider(settings)
        vectors = get_vector_store(settings, dimensions=emb.dimensions)
        ingest = KnowledgeIngestionService(
            knowledge, settings, embeddings=emb, vector_store=vectors
        )
        retrieve = HybridEvidenceRetriever(
            lexical=KnowledgeRetrievalService(knowledge),
            vectors=vectors,
            embeddings=emb,
        )
        delete = KnowledgeDeletionService(knowledge, vector_store=vectors)

        document = ingest.ingest_upload(
            account_id=account.account_id,
            filename="protocolo.txt",
            payload=(
                b"Vigilar fiebre y signos de infeccion en la herida postoperatoria. "
                b"Marker ZXQ-417 for forget verification."
            ),
        )
        assert document["status"] == "AVAILABLE", document
        hits = retrieve.retrieve(account_id=account.account_id, query="ZXQ-417", limit=5)
        assert hits, "expected retrieval hits before delete"
        assert (
            vectors.count_document(
                account_id=account.account_id, document_id=document["document_id"]
            )
            > 0
        )
        assert delete.delete(account_id=account.account_id, document_id=document["document_id"])
        after = retrieve.retrieve(account_id=account.account_id, query="ZXQ-417", limit=5)
        assert after == [], "deleted knowledge must not be retrievable"
        assert (
            vectors.count_document(
                account_id=account.account_id, document_id=document["document_id"]
            )
            == 0
        )
        print(
            f"knowledge_lifecycle_eval[{args.provider}]: "
            "PASS (ingest → hybrid retrieve → forget both)"
        )
        reset_vector_store_for_tests()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
