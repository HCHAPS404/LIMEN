"""Integration: living knowledge lifecycle upload → retrieve → forget."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from limen.config import settings as settings_module
from limen.knowledge.jobs import reset_knowledge_job_runner_for_tests
from limen.persistence.database import reset_database_for_tests

PASSWORD = "umbral-seguro-2026"
PROBE_FACT = (
    "The LIMEN synthetic recovery protocol identifies marker ZXQ-417 "
    "as the unique verification token."
)
PROBE_TOKEN = "ZXQ-417"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "knowledge.db"))
    monkeypatch.setenv("DOCUMENT_PATH", str(tmp_path / "documents"))
    monkeypatch.setenv("VECTOR_PATH", str(tmp_path / "vectors"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")
    monkeypatch.setenv("VECTOR_STORE_BACKEND", "qdrant")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    settings_module.get_settings.cache_clear()
    reset_database_for_tests()
    from limen.knowledge.vector_store import reset_vector_store_for_tests

    reset_vector_store_for_tests()
    reset_knowledge_job_runner_for_tests()
    with TestClient(create_app(settings_module.get_settings())) as test_client:
        yield test_client
    reset_knowledge_job_runner_for_tests()
    reset_vector_store_for_tests()
    reset_database_for_tests()
    settings_module.get_settings.cache_clear()


def _register(client: TestClient, email: str = "knowledge@umbral.io") -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Knowledge Lab"},
    )
    assert response.status_code == 201, response.text


def _wait_status(
    client: TestClient,
    document_id: str,
    *,
    wanted: set[str],
    timeout: float = 8.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        detail = client.get(f"/api/knowledge/documents/{document_id}")
        assert detail.status_code == 200
        last = detail.json()
        if last["status"] in wanted:
            return last
        time.sleep(0.05)
    raise AssertionError(f"timeout waiting for {wanted}; last={last}")


def test_upload_processing_available_list_and_detail(client: TestClient) -> None:
    _register(client)
    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("probe.txt", PROBE_FACT.encode("utf-8"), "text/plain")},
    )
    assert uploaded.status_code == 201, uploaded.text
    document = uploaded.json()
    assert document["status"] in {"UPLOADED", "PROCESSING"}
    document = _wait_status(client, document["document_id"], wanted={"AVAILABLE"})
    assert document["active_version_id"]
    assert document["chunk_count"] and document["chunk_count"] > 0
    assert document["sha256"]
    assert document["failure_stage"] is None

    listed = client.get("/api/knowledge/documents")
    assert listed.status_code == 200
    assert any(item["document_id"] == document["document_id"] for item in listed.json())

    detail = client.get(f"/api/knowledge/documents/{document['document_id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "AVAILABLE"
    assert detail.json()["active_version_id"] == document["active_version_id"]


def test_retrieval_after_upload_carries_provenance(client: TestClient) -> None:
    _register(client)
    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("probe.txt", PROBE_FACT.encode("utf-8"), "text/plain")},
    )
    document = _wait_status(client, uploaded.json()["document_id"], wanted={"AVAILABLE"})
    probe = client.get("/api/knowledge/retrieval-probe", params={"query": PROBE_TOKEN})
    assert probe.status_code == 200
    chunks = probe.json()["chunks"]
    assert chunks
    assert all(chunk["document_id"] == document["document_id"] for chunk in chunks)
    assert all(chunk["version_id"] == document["active_version_id"] for chunk in chunks)
    assert all(chunk.get("filename") or chunk["source_name"] for chunk in chunks)
    assert all(chunk["active"] is True for chunk in chunks)
    assert any(PROBE_TOKEN in chunk["text"] for chunk in chunks)


def test_delete_removed_and_forgotten(client: TestClient) -> None:
    _register(client)
    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("probe.txt", PROBE_FACT.encode("utf-8"), "text/plain")},
    )
    document = _wait_status(client, uploaded.json()["document_id"], wanted={"AVAILABLE"})
    document_id = document["document_id"]
    version_id = document["active_version_id"]

    before = client.get("/api/knowledge/retrieval-probe", params={"query": PROBE_TOKEN})
    assert any(c["document_id"] == document_id for c in before.json()["chunks"])

    deleted = client.delete(f"/api/knowledge/documents/{document_id}")
    assert deleted.status_code == 200
    body = deleted.json()
    assert body["status"] == "REMOVED"
    assert body["document_id"] == document_id

    after = client.get("/api/knowledge/retrieval-probe", params={"query": PROBE_TOKEN})
    assert after.status_code == 200
    assert after.json()["chunks"] == []
    assert not any(c.get("version_id") == version_id for c in after.json()["chunks"])


def test_duplicate_upload_returns_conflict(client: TestClient) -> None:
    _register(client)
    payload = PROBE_FACT.encode("utf-8")
    first = client.post(
        "/api/knowledge/documents",
        files={"file": ("probe-a.txt", payload, "text/plain")},
    )
    assert first.status_code == 201
    _wait_status(client, first.json()["document_id"], wanted={"AVAILABLE"})
    second = client.post(
        "/api/knowledge/documents",
        files={"file": ("probe-b.txt", payload, "text/plain")},
    )
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["code"] == "duplicate_document"
    assert detail["document"]["document_id"] == first.json()["document_id"]


def test_corrupt_pdf_becomes_failed(client: TestClient) -> None:
    _register(client)
    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("broken.pdf", b"%PDF-1.4 not-a-real-pdf", "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    document = _wait_status(
        client, uploaded.json()["document_id"], wanted={"FAILED"}, timeout=8.0
    )
    assert document["failure_stage"]
    assert document["failure_message"]


def test_unsupported_and_empty_rejected(client: TestClient) -> None:
    _register(client)
    empty = client.post(
        "/api/knowledge/documents",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty.status_code == 422

    bad = client.post(
        "/api/knowledge/documents",
        files={"file": ("notes.docx", b"not-supported", "application/octet-stream")},
    )
    assert bad.status_code == 422


def test_delete_nonexistent_and_repeated(client: TestClient) -> None:
    _register(client)
    missing = client.delete("/api/knowledge/documents/does-not-exist")
    assert missing.status_code == 404

    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("once.txt", PROBE_FACT.encode("utf-8"), "text/plain")},
    )
    document_id = uploaded.json()["document_id"]
    _wait_status(client, document_id, wanted={"AVAILABLE"})
    first = client.delete(f"/api/knowledge/documents/{document_id}")
    assert first.status_code == 200
    assert first.json()["status"] == "REMOVED"
    second = client.delete(f"/api/knowledge/documents/{document_id}")
    assert second.status_code == 200
    assert second.json()["status"] == "REMOVED"


def test_knowledge_events_emitted_for_lifecycle(client: TestClient) -> None:
    _register(client, email="events@umbral.io")
    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("events.txt", PROBE_FACT.encode("utf-8"), "text/plain")},
    )
    document_id = uploaded.json()["document_id"]
    _wait_status(client, document_id, wanted={"AVAILABLE"})
    from limen.persistence.database import get_database
    from limen.persistence.repositories.knowledge import SqliteKnowledgeRepository

    settings = settings_module.get_settings()
    repo = SqliteKnowledgeRepository(get_database(settings))
    row = get_database(settings).connection.execute(
        "SELECT account_id FROM documents WHERE document_id = ?",
        (document_id,),
    ).fetchone()
    assert row is not None
    events = repo.list_events(row["account_id"], document_id)
    stages = [event["stage"] for event in events]
    for required in (
        "knowledge.uploaded",
        "knowledge.processing_started",
        "knowledge.parsed",
        "knowledge.chunked",
        "knowledge.indexed",
        "knowledge.dense_indexed",
        "knowledge.available",
    ):
        assert required in stages, stages

    client.delete(f"/api/knowledge/documents/{document_id}")
    after = repo.list_events(row["account_id"], document_id)
    after_stages = [event["stage"] for event in after]
    assert "knowledge.deletion_started" in after_stages
    assert "knowledge.purged" in after_stages
    assert "knowledge.removed" in after_stages
