"""Knowledge transport schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DocumentStatus = Literal[
    "UPLOADED",
    "PROCESSING",
    "AVAILABLE",
    "FAILED",
    "REMOVING",
    "REMOVED",
]


class KnowledgeDocumentResponse(BaseModel):
    document_id: str
    source_name: str
    filename: str | None = None
    status: DocumentStatus
    version: int
    active_version_id: str | None = None
    uploaded_at: datetime | str
    updated_at: datetime | str | None = None
    indexed_at: datetime | str | None = None
    removed_at: datetime | str | None = None
    size_bytes: int | None = None
    page_count: int | None = None
    chunk_count: int | None = None
    sha256: str | None = None
    parser: str | None = None
    ocr_applied: bool | None = None
    failure_stage: str | None = None
    failure_message: str | None = None


class DuplicateDocumentResponse(BaseModel):
    code: Literal["duplicate_document"] = "duplicate_document"
    message: str
    document: KnowledgeDocumentResponse


class EvidenceChunkResponse(BaseModel):
    document_id: str
    chunk_id: str
    text: str
    source_name: str
    filename: str | None = None
    page: int | None = None
    section: str | None = None
    score: float
    version: int
    version_id: str | None = None
    content_hash: str | None = None
    active: bool = True
    retrieval_modes: list[str] = Field(default_factory=list)


class RetrievalProbeResponse(BaseModel):
    query: str
    executed_at: datetime | str
    chunks: list[EvidenceChunkResponse] = Field(default_factory=list)
