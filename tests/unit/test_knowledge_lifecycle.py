"""Unit tests for knowledge lifecycle primitives."""

from __future__ import annotations

import pytest

from limen.knowledge.chunking import chunk_pages, content_hash_text, stable_chunk_id
from limen.knowledge.contracts import KnowledgeStatus
from limen.knowledge.ingestion import storage_basename
from limen.knowledge.lifecycle import InvalidStatusTransition, assert_transition, can_transition
from limen.persistence.repositories.knowledge import sha256_bytes


def test_storage_basename_stays_under_name_max() -> None:
    document_id = "5286bcf9322943b883feaeb1fe408bcd"
    long_name = (
        "Protocolo de recuperación mejorada después de cirugía (ERAS) atenúa el "
        "estrés y acelera la recuperación en pacientes después de resección radical "
        "por cáncer colorrectal- Experiencia en la Clínica Universitaria Colombia.pdf"
    )
    stored = storage_basename(document_id, long_name)
    assert stored == f"{document_id}.pdf"
    assert len(stored.encode("utf-8")) < 180
    assert storage_basename(document_id, "guide.txt") == f"{document_id}.txt"


def test_sha256_fingerprint_is_deterministic() -> None:
    payload = b"LIMEN synthetic recovery protocol marker ZXQ-417"
    assert sha256_bytes(payload) == sha256_bytes(payload)
    assert sha256_bytes(payload) != sha256_bytes(payload + b"x")


def test_status_transitions_allow_canonical_edges_only() -> None:
    assert can_transition(KnowledgeStatus.UPLOADED, KnowledgeStatus.PROCESSING)
    assert can_transition(KnowledgeStatus.PROCESSING, KnowledgeStatus.AVAILABLE)
    assert can_transition(KnowledgeStatus.AVAILABLE, KnowledgeStatus.REMOVING)
    assert can_transition(KnowledgeStatus.REMOVING, KnowledgeStatus.REMOVED)
    assert not can_transition(KnowledgeStatus.UPLOADED, KnowledgeStatus.AVAILABLE)
    assert not can_transition(KnowledgeStatus.REMOVED, KnowledgeStatus.AVAILABLE)
    with pytest.raises(InvalidStatusTransition):
        assert_transition(KnowledgeStatus.REMOVED, KnowledgeStatus.PROCESSING)


def test_chunk_provenance_is_stable_and_page_aware() -> None:
    chunks = chunk_pages(
        document_id="doc1",
        version_id="ver1",
        filename="protocol.pdf",
        pages=[(1, "Alpha paragraph.\n\nBeta paragraph about recovery.")],
    )
    assert chunks
    first = chunks[0]
    assert first.document_id == "doc1"
    assert first.version_id == "ver1"
    assert first.filename == "protocol.pdf"
    assert first.page == 1
    assert first.content_hash == content_hash_text(first.text)
    again = stable_chunk_id(
        document_id="doc1",
        version_id="ver1",
        page=1,
        ordinal=0,
        text_hash=first.content_hash or "",
    )
    assert first.chunk_id == again
