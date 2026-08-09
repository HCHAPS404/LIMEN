"""Deterministic, provenance-aware chunking."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ProvenancedChunk:
    chunk_id: str
    document_id: str
    version_id: str
    filename: str
    page: int | None
    text: str
    ordinal: int
    section: str | None = None
    content_hash: str | None = None


def content_hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_chunk_id(
    *,
    document_id: str,
    version_id: str,
    page: int | None,
    ordinal: int,
    text_hash: str,
) -> str:
    """Stable id for traceability across re-index of the same version content."""
    material = f"{document_id}:{version_id}:{page}:{ordinal}:{text_hash}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def chunk_pages(
    *,
    document_id: str,
    version_id: str,
    filename: str,
    pages: list[tuple[int | None, str]],
    size: int = 700,
    overlap: int = 80,
) -> list[ProvenancedChunk]:
    """Page-aware segmentation; prefer paragraph splits within a page."""
    chunks: list[ProvenancedChunk] = []
    ordinal = 0
    for page, text in pages:
        for piece in _segment_page(text, size=size, overlap=overlap):
            text_hash = content_hash_text(piece)
            chunk_id = stable_chunk_id(
                document_id=document_id,
                version_id=version_id,
                page=page,
                ordinal=ordinal,
                text_hash=text_hash,
            )
            chunks.append(
                ProvenancedChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    version_id=version_id,
                    filename=filename,
                    page=page,
                    text=piece,
                    ordinal=ordinal,
                    content_hash=text_hash,
                )
            )
            ordinal += 1
    return chunks


def _segment_page(text: str, *, size: int, overlap: int) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [" ".join(cleaned.split())]
    pieces: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        normalized = " ".join(paragraph.split())
        if not buffer:
            buffer = normalized
        elif len(buffer) + 1 + len(normalized) <= size:
            buffer = f"{buffer} {normalized}"
        else:
            pieces.extend(_window(buffer, size=size, overlap=overlap))
            buffer = normalized
    if buffer:
        pieces.extend(_window(buffer, size=size, overlap=overlap))
    return pieces


def _window(text: str, *, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        pieces.append(text[start:end])
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return pieces
