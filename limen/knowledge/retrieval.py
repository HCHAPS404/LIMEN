"""Lexical FTS adapter — one half of hybrid retrieval (dense lives elsewhere)."""

from __future__ import annotations

from limen.knowledge.contracts import EvidenceChunk
from limen.persistence.repositories.knowledge import SqliteKnowledgeRepository


def empty_retrieval() -> list[EvidenceChunk]:
    return []


class KnowledgeRetrievalService:
    """SQLite FTS5 adapter used as the lexical path for HybridEvidenceRetriever."""

    def __init__(self, repository: SqliteKnowledgeRepository) -> None:
        self._repository = repository

    def retrieve(
        self,
        *,
        account_id: str,
        query: str,
        limit: int = 5,
    ) -> list[EvidenceChunk]:
        chunks = self._repository.retrieve(
            account_id=account_id, query=query, limit=limit
        )
        return [
            chunk.model_copy(update={"retrieval_modes": ["lexical"]})
            for chunk in chunks
        ]
