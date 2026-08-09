"""HTTP surfaces for calls, knowledge, and traces over the real SQLite schema."""

from __future__ import annotations

import json
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


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "product.db"))
    monkeypatch.setenv("DOCUMENT_PATH", str(tmp_path / "documents"))
    monkeypatch.setenv("VECTOR_PATH", str(tmp_path / "vectors"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")
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


def _register(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "clinica@umbral.io",
            "password": PASSWORD,
            "display_name": "Clínica Umbral",
        },
    )
    assert response.status_code == 201, response.text


def test_call_lifecycle_and_trace(client: TestClient) -> None:
    _register(client)
    created = client.post(
        "/api/calls",
        json={"patient_alias": "Paciente A", "procedure": "apendicectomía", "postoperative_day": 2},
    )
    assert created.status_code == 201
    call_id = created.json()["call_id"]

    listed = client.get("/api/calls")
    assert listed.status_code == 200
    assert any(item["call_id"] == call_id for item in listed.json())

    finished = client.post(f"/api/calls/{call_id}/finish")
    assert finished.status_code == 200
    assert finished.json()["duration_seconds"] is not None

    summary = client.get(f"/api/calls/{call_id}/summary")
    assert summary.status_code == 200
    assert summary.json()["call"]["call_id"] == call_id

    trace = client.get(f"/api/traces/{call_id}")
    assert trace.status_code == 200
    assert trace.json()["call_id"] == call_id
    assert any(event["stage"] == "session_end" for event in trace.json()["events"])


def test_knowledge_upload_retrieve_and_forget(client: TestClient) -> None:
    _register(client)
    content = (
        b"Protocolo postoperatorio: vigilar fiebre, dolor controlado con analgesicos, "
        b"y signos de infeccion en la herida."
    )
    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("protocolo.txt", content, "text/plain")},
    )
    assert uploaded.status_code == 201, uploaded.text
    document = uploaded.json()
    assert document["status"] in {"UPLOADED", "PROCESSING", "AVAILABLE"}
    document_id = document["document_id"]

    import time

    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        detail = client.get(f"/api/knowledge/documents/{document_id}").json()
        if detail["status"] == "AVAILABLE":
            document = detail
            break
        if detail["status"] == "FAILED":
            raise AssertionError(detail)
        time.sleep(0.05)
    else:
        raise AssertionError("document did not become AVAILABLE")

    assert document["chunk_count"] and document["chunk_count"] > 0

    probe = client.get("/api/knowledge/retrieval-probe", params={"query": "fiebre herida"})
    assert probe.status_code == 200
    assert len(probe.json()["chunks"]) >= 1
    assert all(chunk["document_id"] == document_id for chunk in probe.json()["chunks"])

    deleted = client.delete(f"/api/knowledge/documents/{document_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "REMOVED"

    after = client.get("/api/knowledge/retrieval-probe", params={"query": "fiebre herida"})
    assert after.status_code == 200
    assert after.json()["chunks"] == []


def _ws_json(message: dict[str, Any]) -> dict[str, Any] | None:
    if message.get("bytes") is not None:
        return None
    if message.get("json") is not None:
        return message["json"]
    text = message.get("text")
    return json.loads(text) if text else None


def test_websocket_text_turn_emits_safety_events(client: TestClient) -> None:
    _register(client)
    created = client.post("/api/calls", json={"patient_alias": "Paciente B"})
    call_id = created.json()["call_id"]

    with client.websocket_connect(f"/api/calls/{call_id}/stream") as ws:
        first = ws.receive_json()
        assert first["type"] == "call.state"
        ws.send_json({"type": "text", "text": "tengo un poco de dolor"})
        types: list[str] = []
        for _ in range(20):
            event = _ws_json(ws.receive())
            if event is None:
                continue
            types.append(event["type"])
            if event["type"] == "call.safety":
                assert event["payload"]["risk"] in {"GREEN", "YELLOW", "ORANGE", "RED"}
            if (
                event["type"] == "call.state"
                and event["payload"]["state"] == "LISTENING"
                and "call.transcript" in types
                and "call.safety" in types
            ):
                break
        assert "call.transcript" in types
        assert "call.safety" in types
        assert "call.clinical_state" in types
        ws.send_json({"type": "end"})
        ended_types = []
        for _ in range(6):
            event = _ws_json(ws.receive())
            if event is None:
                continue
            ended_types.append(event["type"])
            if event["type"] == "call.ended":
                break
        assert "call.ended" in ended_types


def test_health_ready_and_providers(client: TestClient) -> None:
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] in {"ready", "degraded"}
    providers = client.get("/health/providers")
    assert providers.status_code == 200
    assert providers.json()["llm"]["provider"] == "stub"


def test_metrics_endpoints(client: TestClient) -> None:
    _register(client)
    created = client.post("/api/calls", json={"patient_alias": "Paciente C"})
    call_id = created.json()["call_id"]
    metrics = client.get(f"/api/metrics/calls/{call_id}")
    assert metrics.status_code == 200
    summary = client.get("/api/metrics/summary")
    assert summary.status_code == 200
    assert summary.json()["call_count"] >= 1
