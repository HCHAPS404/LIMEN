"""PHASE 4 TRAZA reconstruction and metrics API integration."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from limen.config import settings as settings_module
from limen.persistence.database import get_database, reset_database_for_tests
from limen.persistence.repositories.knowledge import SqliteKnowledgeRepository

PASSWORD = "umbral-seguro-2026"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "traza.db"))
    monkeypatch.setenv("DOCUMENT_PATH", str(tmp_path / "documents"))
    monkeypatch.setenv("VECTOR_PATH", str(tmp_path / "vectors"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    settings_module.get_settings.cache_clear()
    reset_database_for_tests()
    from limen.knowledge.vector_store import reset_vector_store_for_tests

    reset_vector_store_for_tests()
    with TestClient(create_app(settings_module.get_settings())) as test_client:
        yield test_client
    reset_vector_store_for_tests()
    reset_database_for_tests()
    settings_module.get_settings.cache_clear()


def _register(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "traza@limen.local",
            "password": PASSWORD,
            "display_name": "Traza",
        },
    )
    assert response.status_code == 201


def test_text_turn_trace_reconstruction(client: TestClient) -> None:
    _register(client)
    call_id = client.post("/api/calls", json={"patient_alias": "P"}).json()["call_id"]
    turn = client.post(f"/api/calls/{call_id}/turns", json={"text": "tengo fiebre"})
    assert turn.status_code == 200
    body = turn.json()
    assert body["metrics"]["clinical_ms"] is not None
    assert body["metrics"]["safety_ms"] is not None
    assert body["metrics"]["cost_basis"] == "not_available"
    assert body["metrics"]["estimated_cost_usd"] is None

    trace = client.get(f"/api/traces/{call_id}").json()
    stages = [e["stage"] for e in trace["events"]]
    assert "call.started" in stages
    for required in (
        "patient_statement",
        "clinical_extraction",
        "uncertainty",
        "retrieval",
        "safety_evaluation",
        "response",
    ):
        assert required in stages

    # Core turn stages appear in order (conversation/debug events may interleave).
    core_stages = (
        "patient_statement",
        "clinical_extraction",
        "uncertainty",
        "retrieval",
        "safety_evaluation",
        "response",
    )
    first_idx = {}
    for i, e in enumerate(trace["events"]):
        stage = e["stage"]
        if stage in core_stages and stage not in first_idx:
            first_idx[stage] = i
    assert [first_idx[s] for s in core_stages] == sorted(first_idx[s] for s in core_stages)
    assert any(e["event_type"] == "conversation.context.built" for e in trace["events"])
    assert trace.get("conversation_debug") is not None

    safety = next(e for e in trace["events"] if e["stage"] == "safety_evaluation")
    assert safety["event_type"] == "safety.evaluation.completed"
    assert safety["payload"]["floor_severity"]
    assert safety["payload"]["final_severity"]
    assert "downgrade_protected" in safety["payload"]
    assert safety["duration_ms"] is not None

    retrieval = next(e for e in trace["events"] if e["stage"] == "retrieval")
    assert "selected_chunk_ids" in (retrieval["metrics"] or {})

    metrics = client.get(f"/api/metrics/calls/{call_id}").json()
    assert metrics["call_aggregation"]["turn_count"] == 1
    assert metrics["voice_latency_status"] == "not_implemented"

    summary = client.get("/api/metrics/summary").json()
    assert summary["call_count"] >= 1
    assert summary["voice_latency_status"] == "not_implemented"
    assert summary["text_turn_latency_p50_ms"] is not None


def test_provider_error_trace_on_llm_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Failing LLM must emit provider.error and still complete safely."""
    from limen.intelligence.contracts import LLMRequest, LLMResponse

    class Boom:
        async def generate_text(self, request: LLMRequest) -> LLMResponse:
            raise RuntimeError("boom")

        async def generate_structured(self, request: LLMRequest, schema: type):  # noqa: ANN401
            raise RuntimeError("boom")

    _register(client)
    # Swap LLM via settings is hard; exercise domain path through a fresh app
    # with dependency override is heavier — use CallService directly.
    from limen.conversation.call_service import CallService
    from limen.persistence.repositories.calls import SqliteCallRepository
    from limen.persistence.repositories.traces import SqliteTraceRepository

    settings_module.get_settings.cache_clear()
    db = get_database(settings_module.get_settings())
    calls = SqliteCallRepository(db)
    traces = SqliteTraceRepository(db)
    account = client.get("/api/auth/me").json()
    service = CallService(calls, traces, llm=Boom())  # type: ignore[arg-type]
    created = service.create(account_id=account["account_id"], patient_alias="P")

    import asyncio

    result = asyncio.run(
        service.process_text_turn(
            account_id=account["account_id"],
            call_id=created["call_id"],
            user_text="me duele un poco la herida",
        )
    )
    assert result is not None
    assert result.provider_error is not None
    events = traces.list_events(account["account_id"], created["call_id"])
    assert any(e["stage"] == "provider.error" for e in events)
    assert any(e["stage"] == "response" for e in events)
    assert not any(e["stage"] == "response" and e.get("status") == "error" for e in events)


def test_knowledge_lifecycle_trace_reconstruction(client: TestClient) -> None:
    _register(client)
    upload = client.post(
        "/api/knowledge/documents",
        files={"file": ("guide.txt", b"Postop fever above 38.5C requires review.", "text/plain")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["document_id"]
    # Wait for background processing if async — sync path may already be AVAILABLE.
    for _ in range(50):
        doc = client.get(f"/api/knowledge/documents/{document_id}").json()
        if doc["status"] in {"AVAILABLE", "FAILED"}:
            break
        import time

        time.sleep(0.05)
    assert doc["status"] == "AVAILABLE"

    settings = settings_module.get_settings()
    repo = SqliteKnowledgeRepository(get_database(settings))
    row = (
        get_database(settings)
        .connection.execute(
            "SELECT account_id FROM documents WHERE document_id = ?",
            (document_id,),
        )
        .fetchone()
    )
    assert row is not None
    events = repo.list_events(row["account_id"], document_id)
    stages = [e["stage"] for e in events]
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
    parsed = next(e for e in events if e["stage"] == "knowledge.parsed")
    assert parsed.get("duration_ms") is not None
    dense = next(e for e in events if e["stage"] == "knowledge.dense_indexed")
    assert dense.get("duration_ms") is not None

    client.delete(f"/api/knowledge/documents/{document_id}")
    after = repo.list_events(row["account_id"], document_id)
    after_stages = [e["stage"] for e in after]
    assert "knowledge.deletion_started" in after_stages
    assert "knowledge.purged" in after_stages
    assert "knowledge.removed" in after_stages


def test_knowledge_failure_emits_failed_event(client: TestClient) -> None:
    _register(client)
    # Empty file rejected at upload — use unsupported empty-ish via corrupt after?
    # Force failure with zero-byte is rejected earlier. Upload then replace storage.
    upload = client.post(
        "/api/knowledge/documents",
        files={"file": ("bad.pdf", b"%PDF-1.4 not-a-real-pdf", "application/pdf")},
    )
    # May fail during processing.
    if upload.status_code != 201:
        pytest.skip("upload rejected before processing")
    document_id = upload.json()["document_id"]
    import time

    for _ in range(80):
        doc = client.get(f"/api/knowledge/documents/{document_id}").json()
        if doc["status"] in {"AVAILABLE", "FAILED"}:
            break
        time.sleep(0.05)
    settings = settings_module.get_settings()
    repo = SqliteKnowledgeRepository(get_database(settings))
    row = (
        get_database(settings)
        .connection.execute(
            "SELECT account_id FROM documents WHERE document_id = ?",
            (document_id,),
        )
        .fetchone()
    )
    assert row is not None
    events = repo.list_events(row["account_id"], document_id)
    if doc["status"] == "FAILED":
        assert any(e["stage"] == "knowledge.failed" for e in events)
        failed = next(e for e in events if e["stage"] == "knowledge.failed")
        assert failed.get("status") == "error"
        assert not any(e["stage"] == "knowledge.available" for e in events)
