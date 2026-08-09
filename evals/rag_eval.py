#!/usr/bin/env python3
"""RAG evaluation — stub (CI) and real E5 providers reported separately."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from limen.auth import AuthService
from limen.config.settings import ApplicationSettings
from limen.knowledge.contracts import RetrievalConfig
from limen.knowledge.deletion import KnowledgeDeletionService
from limen.knowledge.embeddings import build_embedding_provider, default_dense_min_score
from limen.knowledge.hybrid import HybridEvidenceRetriever
from limen.knowledge.ingestion import KnowledgeIngestionService
from limen.knowledge.retrieval import KnowledgeRetrievalService
from limen.knowledge.vector_store import get_vector_store, reset_vector_store_for_tests
from limen.persistence.database import Database
from limen.persistence.repositories.accounts import SqliteAccountRepository
from limen.persistence.repositories.knowledge import SqliteKnowledgeRepository

# Shared lexical / exact probes (work for stub and real).
BASE_CORPUS: list[tuple[str, str]] = [
    (
        "protocol_zxq.txt",
        "The LIMEN synthetic recovery protocol identifies marker ZXQ-417 "
        "as the unique verification token. Temperature threshold noted as 38.5C.",
    ),
    (
        "diet_es.txt",
        "Tras la cirugia se recomienda hidratacion oral frecuente y dieta blanda "
        "durante las primeras 48 horas. Medication reference: acetaminophen 500mg.",
    ),
]

# Bilingual semantic corpus for real E5 / expanded stub hybrid checks.
BILINGUAL_CORPUS: list[tuple[str, str]] = [
    (
        "serous_drainage_en.txt",
        "Serous wound drainage may appear as clear or pale fluid seeping from the "
        "incision in early recovery and should be monitored for volume change.",
    ),
    (
        "dyspnea_en.txt",
        "Shortness of breath (dyspnea) after surgery requires prompt clinical review, "
        "especially when the patient reports air hunger or difficulty breathing.",
    ),
    (
        "dehiscence_en.txt",
        "Partial wound dehiscence means the surgical incision has opened slightly; "
        "patients may notice edges separating without full rupture.",
    ),
    (
        "erythema_en.txt",
        "Peri-incisional erythema with warmth can indicate local inflammation or "
        "early surgical site infection and warrants observation.",
    ),
]

BASE_PROBES: list[dict[str, Any]] = [
    {"query": "ZXQ-417", "relevant_files": ["protocol_zxq.txt"], "kind": "exact"},
    {
        "query": "38.5C",
        "relevant_files": ["protocol_zxq.txt"],
        "kind": "numeric",
    },
    {
        "query": "acetaminophen 500mg",
        "relevant_files": ["diet_es.txt"],
        "kind": "medication",
    },
    {
        "query": "dieta blanda hidratacion",
        "relevant_files": ["diet_es.txt"],
        "kind": "lexical_es",
    },
]

NONE_PROBES = {
    "stub": {
        "query": "unrelated quantum pineapple theorem",
        "relevant_files": [],
        "kind": "none",
    },
    "real": {
        "query": "configuración del router WiFi canal once y resultados de la liga",
        "relevant_files": [],
        "kind": "none",
    },
}

BILINGUAL_PROBES: list[dict[str, Any]] = [
    {
        "query": "me está saliendo como agüita de la herida",
        "relevant_files": ["serous_drainage_en.txt"],
        "kind": "bilingual_colloquial",
    },
    {
        "query": "me falta el aire",
        "relevant_files": ["dyspnea_en.txt"],
        "kind": "bilingual_colloquial",
    },
    {
        "query": "se me abrió un poquito la herida",
        "relevant_files": ["dehiscence_en.txt"],
        "kind": "bilingual_colloquial",
    },
    {
        "query": "la herida está roja y caliente",
        "relevant_files": ["erythema_en.txt"],
        "kind": "bilingual_standard",
    },
    {
        "query": "serous drainage from incision",
        "relevant_files": ["serous_drainage_en.txt"],
        "kind": "english_paraphrase",
    },
]


def _hit_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if any(doc_id in relevant for doc_id in ranked_ids[:k]) else 0.0


def _mrr(ranked_ids: list[str], relevant: set[str]) -> float:
    for idx, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in relevant:
            return 1.0 / idx
    return 0.0


def _settings_for(provider: str, root: Path) -> ApplicationSettings:
    import os

    if provider == "stub":
        return ApplicationSettings(
            DATABASE_PATH=root / "rag.db",
            DOCUMENT_PATH=root / "documents",
            VECTOR_PATH=root / "vectors",
            EMBEDDING_PROVIDER="stub",
            EMBEDDING_DIMENSIONS=64,
            VECTOR_STORE_BACKEND="qdrant",
            LLM_PROVIDER="stub",
            _env_file=None,
        )
    path = os.environ.get("EMBEDDING_MODEL_PATH", "").strip()
    kwargs: dict[str, object] = {
        "DATABASE_PATH": root / "rag.db",
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
    return ApplicationSettings(**kwargs)  # type: ignore[arg-type]


def run_eval(*, provider: str) -> dict[str, Any]:
    corpus = list(BASE_CORPUS)
    probes = list(BASE_PROBES)
    probes.append(NONE_PROBES[provider if provider in NONE_PROBES else "stub"])
    if provider == "real":
        corpus.extend(BILINGUAL_CORPUS)
        probes.extend(BILINGUAL_PROBES)
    else:
        # Stub keeps a bilingual-ish overlapping probe without requiring E5.
        corpus.append(
            (
                "wound_en.txt",
                "Signos de infeccion de herida postoperatoria / postoperative wound "
                "infection: erythema, purulent drainage, fiebre above 38.5C after day 3.",
            )
        )
        probes.insert(
            1,
            {
                "query": "fiebre herida infeccion",
                "relevant_files": ["wound_en.txt"],
                "kind": "semantic_stub",
            },
        )

    timings: dict[str, float] = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings = _settings_for(provider, root)
        settings.ensure_runtime_dirs()
        reset_vector_store_for_tests()

        t0 = time.perf_counter()
        emb = build_embedding_provider(settings)
        # Force model load for real provider timing.
        _ = emb.dimensions
        timings["embedding_init_ms"] = (time.perf_counter() - t0) * 1000.0

        t_first = time.perf_counter()
        _ = emb.embed_query("warmup probe cold")
        timings["first_query_embed_ms"] = (time.perf_counter() - t_first) * 1000.0

        t_warm = time.perf_counter()
        _ = emb.embed_query("warmup probe warm")
        timings["warm_query_embed_ms"] = (time.perf_counter() - t_warm) * 1000.0

        database = Database(settings.database_path)
        database.initialize()
        auth = AuthService(SqliteAccountRepository(database))
        account = auth.register("rag@limen.local", "rag-password-2026", "RAG").account
        knowledge = SqliteKnowledgeRepository(database)
        vectors = get_vector_store(settings, dimensions=emb.dimensions)
        min_score = default_dense_min_score(settings)
        ingest = KnowledgeIngestionService(
            knowledge, settings, embeddings=emb, vector_store=vectors
        )
        hybrid = HybridEvidenceRetriever(
            lexical=KnowledgeRetrievalService(knowledge),
            vectors=vectors,
            embeddings=emb,
            config=RetrievalConfig(dense_min_score=min_score),
        )
        lexical_only = KnowledgeRetrievalService(knowledge)

        file_to_doc: dict[str, str] = {}
        t_embed = 0.0
        for filename, text in corpus:
            t1 = time.perf_counter()
            doc = ingest.ingest_upload(
                account_id=account.account_id,
                filename=filename,
                payload=text.encode("utf-8"),
            )
            t_embed += time.perf_counter() - t1
            assert doc["status"] == "AVAILABLE", doc
            file_to_doc[filename] = doc["document_id"]
        timings["document_embedding_total_ms"] = t_embed * 1000.0

        hit_scores: list[float] = []
        mrr_scores: list[float] = []
        bilingual_hits: list[float] = []
        lexical_hits: list[float] = []
        hybrid_hits: list[float] = []
        provenance_ok = 0
        provenance_n = 0
        no_evidence_ok = 0
        probe_rows: list[dict[str, Any]] = []

        for probe in probes:
            relevant_docs = {file_to_doc[name] for name in probe["relevant_files"]}
            t_h = time.perf_counter()
            hits = hybrid.retrieve(account_id=account.account_id, query=probe["query"], limit=5)
            timings["hybrid_retrieval_ms"] = (time.perf_counter() - t_h) * 1000.0
            metrics = hybrid.last_metrics
            ranked = [h.document_id for h in hits]
            lex_hits = lexical_only.retrieve(
                account_id=account.account_id, query=probe["query"], limit=5
            )
            lex_ranked = [h.document_id for h in lex_hits]

            row: dict[str, Any] = {
                "query": probe["query"],
                "kind": probe["kind"],
                "hybrid_hit@5": None,
                "lexical_hit@5": None,
                "dense_candidates": metrics.get("dense_candidates"),
                "lexical_candidates": metrics.get("lexical_candidates"),
            }
            if not relevant_docs:
                no_evidence_ok += int(len(hits) == 0)
                row["hybrid_hit@5"] = 1.0 if not hits else 0.0
            else:
                h = _hit_at_k(ranked, relevant_docs, k=5)
                m = _mrr(ranked, relevant_docs)
                lh = _hit_at_k(lex_ranked, relevant_docs, k=5)
                hit_scores.append(h)
                mrr_scores.append(m)
                hybrid_hits.append(h)
                lexical_hits.append(lh)
                row["hybrid_hit@5"] = h
                row["lexical_hit@5"] = lh
                row["mrr"] = m
                if str(probe["kind"]).startswith("bilingual"):
                    bilingual_hits.append(h)
            for chunk in hits:
                provenance_n += 1
                if (
                    chunk.document_id
                    and chunk.chunk_id
                    and (chunk.filename or chunk.source_name)
                    and chunk.version_id
                ):
                    provenance_ok += 1
            timings["dense_query_ms"] = float(metrics.get("dense_ms", 0.0))
            timings["lexical_query_ms"] = float(metrics.get("lexical_ms", 0.0))
            timings["fusion_ms"] = float(metrics.get("fusion_ms", 0.0))
            probe_rows.append(row)

        zxq_id = file_to_doc["protocol_zxq.txt"]
        KnowledgeDeletionService(knowledge, vector_store=vectors).delete(
            account_id=account.account_id, document_id=zxq_id
        )
        after = hybrid.retrieve(account_id=account.account_id, query="ZXQ-417", limit=5)
        leakage = sum(1 for h in after if h.document_id == zxq_id)
        dense_left = vectors.count_document(account_id=account.account_id, document_id=zxq_id)

        # Exact lexical must not regress vs lexical-only baseline on exact probes.
        exact_ok = True
        for row in probe_rows:
            lexical_hit = row.get("lexical_hit@5")
            hybrid_hit = row.get("hybrid_hit@5")
            if (
                row["kind"] in {"exact", "numeric", "medication"}
                and lexical_hit is not None
                and hybrid_hit is not None
                and hybrid_hit < lexical_hit
            ):
                exact_ok = False

        report: dict[str, Any] = {
            "provider_mode": provider,
            "provider": settings.embedding_provider,
            "model": settings.embedding_model if provider == "real" else emb.model_id,  # type: ignore[attr-defined]
            "dimensions": emb.dimensions,
            "dense_min_score": min_score,
            "vector_backend": settings.vector_store_backend,
            "hit_at_5": (sum(hit_scores) / len(hit_scores)) if hit_scores else None,
            "mrr": (sum(mrr_scores) / len(mrr_scores)) if mrr_scores else None,
            "bilingual_hit_at_5": (
                (sum(bilingual_hits) / len(bilingual_hits)) if bilingual_hits else None
            ),
            "lexical_hit_at_5_mean": (
                (sum(lexical_hits) / len(lexical_hits)) if lexical_hits else None
            ),
            "hybrid_hit_at_5_mean": (
                (sum(hybrid_hits) / len(hybrid_hits)) if hybrid_hits else None
            ),
            "exact_lexical_not_regressed": exact_ok,
            "citation_provenance_validity": (provenance_ok / provenance_n if provenance_n else 1.0),
            "no_evidence_behavior_pass_rate": no_evidence_ok
            / max(1, sum(1 for p in probes if not p["relevant_files"])),
            "deleted_document_leakage_rate": float(leakage),
            "dense_vectors_remaining_after_delete": dense_left,
            "timings_ms": timings,
            "probes": probe_rows,
            "notes": (
                f"Synthetic/local evaluation only. Not a challenge benchmark. Mode={provider}."
            ),
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        assert report["hit_at_5"] == 1.0, report
        assert report["citation_provenance_validity"] == 1.0, report
        assert report["deleted_document_leakage_rate"] == 0.0, report
        assert report["dense_vectors_remaining_after_delete"] == 0
        assert report["exact_lexical_not_regressed"] is True
        if provider == "stub":
            assert report["mrr"] is not None and report["mrr"] >= 0.8, report
            assert report["no_evidence_behavior_pass_rate"] == 1.0, report
        else:
            # Real E5: Hit@K and bilingual success are gates; MRR may be <1 when
            # several clinically related docs compete in Top-K.
            assert report["mrr"] is not None and report["mrr"] >= 0.5, report
            assert report["bilingual_hit_at_5"] == 1.0, report
            assert report["no_evidence_behavior_pass_rate"] == 1.0, report
        print(f"rag_eval[{provider}]: PASS")
        database.close()
        reset_vector_store_for_tests()
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description="LIMEN RAG evaluation harness")
    parser.add_argument(
        "--provider",
        choices=("stub", "real"),
        default="stub",
        help="stub = deterministic CI; real = multilingual-e5-small",
    )
    args = parser.parse_args()
    run_eval(provider=args.provider)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
