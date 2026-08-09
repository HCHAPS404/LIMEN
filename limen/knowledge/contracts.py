"""Knowledge and embedding contracts with provenance."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, model_validator


class KnowledgeStatus(StrEnum):
    """Canonical document lifecycle statuses (PHASE 2).

    AVAILABLE requires verified indexing. REMOVED requires verified purge.
    """

    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    AVAILABLE = "AVAILABLE"
    FAILED = "FAILED"
    REMOVING = "REMOVING"
    REMOVED = "REMOVED"


class RetrievalQuery(BaseModel):
    """Typed retrieval request — filters are optional and must not over-constrain."""

    text: str
    account_id: str
    procedure: str | None = None
    postoperative_day: int | None = None
    clinical_concepts: list[str] = Field(default_factory=list)
    top_k: int = 5


class RetrievalConfig(BaseModel):
    """Hybrid retrieval knobs — no scattered magic numbers."""

    dense_top_k: int = 8
    lexical_top_k: int = 8
    final_top_k: int = 5
    rrf_k: int = 60
    dense_min_score: float = 0.35


class EvidenceChunk(BaseModel):
    """Typed evidence — retrieved content is untrusted data, never system policy."""

    document_id: str
    chunk_id: str
    text: str
    source_name: str
    page: int | None = None
    score: float = 0.0
    version: int = 1
    version_id: str | None = None
    filename: str | None = None
    section: str | None = None
    content_hash: str | None = None
    active: bool = True
    retrieval_modes: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _alias_filename(self) -> EvidenceChunk:
        if not self.filename:
            self.filename = self.source_name
        return self


class EvidenceRetriever(Protocol):
    """Provider-neutral retrieval surface for conversation orchestration.

    Lexical FTS, dense, or hybrid backends may implement this without changing
    ConversationOrchestrator.
    """

    def retrieve(
        self,
        *,
        account_id: str,
        query: str,
        limit: int = 5,
    ) -> list[EvidenceChunk]: ...


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...

    @property
    def dimensions(self) -> int: ...
