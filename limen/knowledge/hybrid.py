"""Hybrid EvidenceRetriever — dense + lexical fusion behind one contract."""

from __future__ import annotations

import time
from typing import Any

from limen.knowledge.contracts import (
    EmbeddingProvider,
    EvidenceChunk,
    RetrievalConfig,
    RetrievalQuery,
)
from limen.knowledge.fusion import reciprocal_rank_fusion
from limen.knowledge.retrieval import KnowledgeRetrievalService
from limen.knowledge.vector_store import VectorStore


class HybridEvidenceRetriever:
    """Orchestrator-facing retriever. Callers must not know the backend mix."""

    def __init__(
        self,
        *,
        lexical: KnowledgeRetrievalService,
        vectors: VectorStore,
        embeddings: EmbeddingProvider,
        config: RetrievalConfig | None = None,
    ) -> None:
        self._lexical = lexical
        self._vectors = vectors
        self._embeddings = embeddings
        self._config = config or RetrievalConfig()
        self.last_metrics: dict[str, Any] = {}

    def retrieve(
        self,
        *,
        account_id: str,
        query: str,
        limit: int = 5,
    ) -> list[EvidenceChunk]:
        request = RetrievalQuery(
            text=query,
            account_id=account_id,
            top_k=limit,
        )
        return self.retrieve_query(request)

    def retrieve_query(self, request: RetrievalQuery) -> list[EvidenceChunk]:
        cleaned = request.text.strip()
        final_k = min(request.top_k, self._config.final_top_k)
        if not cleaned:
            self.last_metrics = {
                "retrieval_query": "",
                "dense_ms": 0.0,
                "lexical_ms": 0.0,
                "fusion_ms": 0.0,
                "dense_candidates": 0,
                "lexical_candidates": 0,
                "final_evidence_count": 0,
                "selected_chunk_ids": [],
                "selected_document_ids": [],
            }
            return []

        dense_limit = max(final_k, self._config.dense_top_k)
        lexical_limit = max(final_k, self._config.lexical_top_k)

        t0 = time.perf_counter()
        query_vector = self._embeddings.embed_query(cleaned)
        dense = self._vectors.search(
            account_id=request.account_id,
            vector=query_vector,
            limit=dense_limit,
        )
        dense = [
            chunk
            for chunk in dense
            if chunk.score >= self._config.dense_min_score
        ]
        dense_ms = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        lexical_raw = self._lexical.retrieve(
            account_id=request.account_id,
            query=cleaned,
            limit=lexical_limit,
        )
        lexical = [
            chunk.model_copy(update={"retrieval_modes": ["lexical"]})
            for chunk in lexical_raw
        ]
        lexical_ms = (time.perf_counter() - t1) * 1000.0

        t2 = time.perf_counter()
        fused = reciprocal_rank_fusion(
            [dense, lexical],
            k=self._config.rrf_k,
            limit=final_k,
        )
        fusion_ms = (time.perf_counter() - t2) * 1000.0

        self.last_metrics = {
            "retrieval_query": cleaned[:240],
            "dense_ms": round(dense_ms, 3),
            "lexical_ms": round(lexical_ms, 3),
            "fusion_ms": round(fusion_ms, 3),
            "dense_candidates": len(dense),
            "lexical_candidates": len(lexical),
            "final_evidence_count": len(fused),
            "selected_chunk_ids": [c.chunk_id for c in fused],
            "selected_document_ids": sorted({c.document_id for c in fused}),
            "retrieval_modes": sorted(
                {mode for chunk in fused for mode in chunk.retrieval_modes}
            ),
        }
        return fused
