"""PHASE 3 unit tests — embeddings, RRF, hybrid provenance, no-evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from limen.config.settings import ApplicationSettings
from limen.knowledge.contracts import EvidenceChunk, RetrievalConfig
from limen.knowledge.embeddings import (
    StubEmbeddingProvider,
    build_embedding_provider,
    format_e5_passage,
    format_e5_query,
    uses_e5_prefixes,
)
from limen.knowledge.fusion import reciprocal_rank_fusion
from limen.knowledge.hybrid import HybridEvidenceRetriever
from limen.knowledge.retrieval import KnowledgeRetrievalService
from limen.knowledge.vector_store import (
    QdrantVectorStore,
    get_vector_store,
    reset_vector_store_for_tests,
)
from limen.persistence.database import Database
from limen.persistence.repositories.knowledge import SqliteKnowledgeRepository


@pytest.fixture(autouse=True)
def _reset_vectors() -> None:
    reset_vector_store_for_tests()
    yield
    reset_vector_store_for_tests()


def test_e5_prefix_helpers_stay_in_adapter() -> None:
    assert uses_e5_prefixes("intfloat/multilingual-e5-small")
    assert not uses_e5_prefixes("BAAI/bge-small-en-v1.5")
    assert format_e5_query("hola") == "query: hola"
    assert format_e5_passage("texto") == "passage: texto"


def test_stub_embedding_provider_contract() -> None:
    provider = StubEmbeddingProvider(dimensions=32)
    docs = provider.embed_documents(["fiebre postoperatoria", "herida limpia"])
    assert len(docs) == 2
    assert all(len(v) == 32 for v in docs)
    query = provider.embed_query("fiebre")
    assert len(query) == 32
    assert abs(sum(x * x for x in query) - 1.0) < 1e-6


def test_build_embedding_provider_stub_from_settings() -> None:
    settings = ApplicationSettings(
        EMBEDDING_PROVIDER="stub",
        EMBEDDING_DIMENSIONS=48,
        _env_file=None,
    )
    emb = build_embedding_provider(settings)
    assert emb.dimensions == 48


def test_rrf_fuses_and_deduplicates() -> None:
    a = EvidenceChunk(
        document_id="d1",
        chunk_id="c1",
        text="token A",
        source_name="a.txt",
        retrieval_modes=["dense"],
        score=0.9,
    )
    b = EvidenceChunk(
        document_id="d1",
        chunk_id="c1",
        text="token A longer",
        source_name="a.txt",
        retrieval_modes=["lexical"],
        score=0.5,
    )
    c = EvidenceChunk(
        document_id="d2",
        chunk_id="c2",
        text="token B",
        source_name="b.txt",
        retrieval_modes=["dense"],
        score=0.8,
    )
    fused = reciprocal_rank_fusion([[a, c], [b]], k=60, limit=5)
    assert len(fused) == 2
    by_id = {chunk.chunk_id: chunk for chunk in fused}
    assert by_id["c1"].retrieval_modes == ["dense", "lexical"]
    assert by_id["c1"].score > by_id["c2"].score


def test_rrf_empty_lists_yield_no_evidence() -> None:
    assert reciprocal_rank_fusion([[], []], limit=5) == []


def test_qdrant_inactive_filter_and_delete(tmp_path: Path) -> None:
    store = QdrantVectorStore(
        tmp_path / "vectors",
        dimensions=8,
        fingerprint="stub|stub-d8|d8|cosine",
    )
    emb = StubEmbeddingProvider(dimensions=8)
    chunk = EvidenceChunk(
        document_id="doc-1",
        chunk_id="chunk-1",
        text="ZXQ-417 marker protocol",
        source_name="p.txt",
        filename="p.txt",
        version_id="v1",
        page=1,
        active=True,
        retrieval_modes=["dense"],
    )
    store.upsert_chunks(
        account_id="acc",
        chunks=[chunk],
        vectors=emb.embed_documents([chunk.text]),
    )
    hits = store.search(
        account_id="acc",
        vector=emb.embed_query("ZXQ-417"),
        limit=3,
    )
    assert hits
    assert hits[0].document_id == "doc-1"
    assert hits[0].chunk_id == "chunk-1"
    assert hits[0].version_id == "v1"

    store.delete_document(account_id="acc", document_id="doc-1")
    assert store.count_document(account_id="acc", document_id="doc-1") == 0
    assert store.search(account_id="acc", vector=emb.embed_query("ZXQ-417"), limit=3) == []
    store.close()


def test_hybrid_no_evidence_and_provenance(tmp_path: Path) -> None:
    settings = ApplicationSettings(
        DATABASE_PATH=tmp_path / "hybrid.db",
        DOCUMENT_PATH=tmp_path / "docs",
        VECTOR_PATH=tmp_path / "vectors",
        EMBEDDING_PROVIDER="stub",
        EMBEDDING_DIMENSIONS=64,
        VECTOR_STORE_BACKEND="qdrant",
        _env_file=None,
    )
    settings.ensure_runtime_dirs()
    db = Database(settings.database_path)
    db.initialize()
    knowledge = SqliteKnowledgeRepository(db)
    emb = build_embedding_provider(settings)
    vectors = get_vector_store(settings, dimensions=emb.dimensions)
    hybrid = HybridEvidenceRetriever(
        lexical=KnowledgeRetrievalService(knowledge),
        vectors=vectors,
        embeddings=emb,
        config=RetrievalConfig(dense_top_k=4, lexical_top_k=4, final_top_k=3, rrf_k=60),
    )
    assert hybrid.retrieve(account_id="acc", query="anything", limit=3) == []
    assert hybrid.last_metrics["final_evidence_count"] == 0
    assert hybrid.retrieve(account_id="acc", query="   ", limit=3) == []
    db.close()
