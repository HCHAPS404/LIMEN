"""Optional real-embedding integration tests.

Skipped unless LIMEN_REAL_EMBEDDINGS=1 (model download + CPU time).

CI uses stub embeddings only. Run real validation via:

  make verify-rag-real
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from limen.config.settings import ApplicationSettings
from limen.knowledge.embeddings import uses_e5_prefixes
from limen.knowledge.vector_store import QdrantVectorStore, reset_vector_store_for_tests

pytestmark = pytest.mark.real_embeddings

_REAL = os.environ.get("LIMEN_REAL_EMBEDDINGS", "").strip() in {"1", "true", "yes"}


def test_e5_model_loads_and_prefixes_apply() -> None:
    if not _REAL:
        pytest.skip("Set LIMEN_REAL_EMBEDDINGS=1 to run real embedding tests")
    assert uses_e5_prefixes("intfloat/multilingual-e5-small")
    from limen.config.settings import ApplicationSettings
    from limen.knowledge.embeddings import build_embedding_provider

    settings = ApplicationSettings(
        EMBEDDING_PROVIDER="sentence-transformers",
        EMBEDDING_MODEL="intfloat/multilingual-e5-small",
        _env_file=None,
    )
    path = os.environ.get("EMBEDDING_MODEL_PATH", "").strip()
    if path:
        settings = ApplicationSettings(
            EMBEDDING_PROVIDER="sentence-transformers",
            EMBEDDING_MODEL="intfloat/multilingual-e5-small",
            EMBEDDING_MODEL_PATH=path,
            _env_file=None,
        )
    emb = build_embedding_provider(settings)
    assert emb.dimensions == 384
    q = emb.embed_query("me falta el aire")
    d = emb.embed_documents(["Shortness of breath / dyspnea"])[0]
    assert len(q) == 384 and len(d) == 384
    # Normalized vectors → cosine ≈ dot product; relevant pair should score high.
    score = sum(a * b for a, b in zip(q, d, strict=True))
    assert score > 0.45


def test_fingerprint_recreates_incompatible_collection(tmp_path: Path) -> None:
    reset_vector_store_for_tests()
    path = tmp_path / "vectors"
    stub = QdrantVectorStore(
        path, dimensions=64, fingerprint="stub|stub-d64|d64|cosine"
    )
    from limen.knowledge.contracts import EvidenceChunk
    from limen.knowledge.embeddings import StubEmbeddingProvider

    emb = StubEmbeddingProvider(64)
    chunk = EvidenceChunk(
        document_id="d1",
        chunk_id="c1",
        text="hello",
        source_name="a.txt",
        version_id="v1",
    )
    stub.upsert_chunks(
        account_id="a", chunks=[chunk], vectors=emb.embed_documents([chunk.text])
    )
    assert stub.count_document(account_id="a", document_id="d1") == 1
    stub.close()
    reset_vector_store_for_tests()

    # Switching fingerprint/dimensions must drop stale vectors.
    e5ish = QdrantVectorStore(
        path,
        dimensions=384,
        fingerprint="sentence-transformers|intfloat/multilingual-e5-small|d384|cosine",
    )
    assert e5ish.count_document(account_id="a", document_id="d1") == 0
    meta = (path / "embedding_index.json").read_text(encoding="utf-8")
    assert "d384" in meta or "384" in meta
    e5ish.close()
    reset_vector_store_for_tests()


def test_settings_default_dense_min_score_provider_aware() -> None:
    from limen.knowledge.embeddings import default_dense_min_score

    stub = ApplicationSettings(EMBEDDING_PROVIDER="stub", _env_file=None)
    real = ApplicationSettings(
        EMBEDDING_PROVIDER="sentence-transformers",
        EMBEDDING_MODEL="intfloat/multilingual-e5-small",
        _env_file=None,
    )
    assert default_dense_min_score(stub) == 0.35
    assert default_dense_min_score(real) == 0.795
    forced = ApplicationSettings(
        EMBEDDING_PROVIDER="sentence-transformers",
        DENSE_MIN_SCORE=0.6,
        _env_file=None,
    )
    assert default_dense_min_score(forced) == 0.6
