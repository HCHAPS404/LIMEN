"""Knowledge and embedding contracts with provenance."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field


class KnowledgeStatus(StrEnum):
    UPLOADING = "UPLOADING"
    INDEXING = "INDEXING"
    AVAILABLE = "AVAILABLE"
    REMOVED = "REMOVED"
    FAILED = "FAILED"


class EvidenceChunk(BaseModel):
    """Typed evidence object returned by retrieval — never treat as system instruction."""

    document_id: str
    chunk_id: str
    text: str
    source_name: str
    page: int | None = None
    score: float = 0.0
    version: int = 1
    metadata: dict[str, str] = Field(default_factory=dict)


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...
