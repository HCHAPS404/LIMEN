"""PHASE 7 golden full-system integration (stub providers — CI-safe).

Proves one coherent application path:
create call → multi-turn → RAG evidence → SafetyDecision → response →
finish → summary → TRAZA → metrics → knowledge upload/forget.

Real challenge providers are verified by ``verify-challenge-environment``.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from limen.config import settings as settings_module
from limen.knowledge.jobs import reset_knowledge_job_runner_for_tests
from limen.persistence.database import reset_database_for_tests

PASSWORD = "umbral-seguro-2026"
UNIQUE_FACT = "LIMEN_GOLDEN_FACT_QX91_POSTOP_SEED"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "golden.db"))
    monkeypatch.setenv("DOCUMENT_PATH", str(tmp_path / "documents"))
    monkeypatch.setenv("VECTOR_PATH", str(tmp_path / "vectors"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STT_PROVIDER", "stub")
    monkeypatch.setenv("TTS_PROVIDER", "stub")
    monkeypatch.setenv("LIMEN_RUNTIME_PROFILE", "development")
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
            "email": "golden@limen.local",
            "password": PASSWORD,
            "display_name": "Golden",
        },
    )
    assert response.status_code == 201, response.text


def test_golden_full_system_green_yellow_red_and_knowledge(client: TestClient) -> None:
    _register(client)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "runtime_profile" in health.json()
    assert "stub_providers" in health.json()

    providers = client.get("/health/providers")
    assert providers.status_code == 200
    body = providers.json()
    assert "llm" in body and "stt" in body and "tts" in body and "embedding" in body
    assert "vector_store" in body

    # --- G5-ish unique document ---
    payload = (
        f"Protocolo golden: {UNIQUE_FACT}. "
        "Tras cirugia observar herida y fiebre.\n"
    ).encode()
    upload = client.post(
        "/api/knowledge/documents",
        files={"file": ("golden_unique.txt", payload, "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["document_id"]

    deadline = time.monotonic() + 12.0
    document = upload.json()
    while time.monotonic() < deadline:
        detail = client.get(f"/api/knowledge/documents/{document_id}").json()
        document = detail
        if detail["status"] == "AVAILABLE":
            break
        if detail["status"] == "FAILED":
            raise AssertionError(detail)
        time.sleep(0.05)
    else:
        raise AssertionError(f"document did not become AVAILABLE: {document}")
    assert document["status"] == "AVAILABLE"

    probe = client.get(
        "/api/knowledge/retrieval-probe",
        params={"query": UNIQUE_FACT},
    )
    assert probe.status_code == 200
    assert len(probe.json()["chunks"]) >= 1
    assert all(c["document_id"] == document_id for c in probe.json()["chunks"])

    # --- Multi-turn call ---
    created = client.post(
        "/api/calls",
        json={
            "patient_alias": "Paciente Golden",
            "procedure": "apendicectomía",
            "postoperative_day": 3,
        },
    )
    assert created.status_code == 201
    call_id = created.json()["call_id"]

    t1 = client.post(
        f"/api/calls/{call_id}/turns",
        json={"text": "Me duele un poco la herida pero estoy bien."},
    )
    assert t1.status_code == 200
    assert t1.json()["assistant_text"]
    assert t1.json()["safety"]["risk"] in {"GREEN", "YELLOW"}

    t2 = client.post(
        f"/api/calls/{call_id}/turns",
        json={"text": f"Segun la guia, que implica {UNIQUE_FACT}?"},
    )
    assert t2.status_code == 200
    assert t2.json()["assistant_text"]

    t3 = client.post(
        f"/api/calls/{call_id}/turns",
        json={"text": "Tengo un poco de fiebre desde ayer."},
    )
    assert t3.status_code == 200
    assert t3.json()["safety"]["risk"] in {"YELLOW", "ORANGE", "RED"}

    finished = client.post(f"/api/calls/{call_id}/finish")
    assert finished.status_code == 200

    summary = client.get(f"/api/calls/{call_id}/summary")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["call"]["call_id"] == call_id
    structured = summary_body.get("summary") or {}
    assert "patient" in structured or "reported_findings" in structured or structured == {}
    # Prefer structured content when present
    if structured:
        assert "patient" in structured
        assert "risk" in structured or "escalated" in structured

    trace = client.get(f"/api/traces/{call_id}")
    assert trace.status_code == 200
    stages = [e["stage"] for e in trace.json()["events"]]
    for required in (
        "call.started",
        "patient_statement",
        "clinical_extraction",
        "uncertainty",
        "retrieval",
        "safety_evaluation",
        "response",
        "session_end",
    ):
        assert required in stages

    metrics = client.get(f"/api/metrics/calls/{call_id}")
    assert metrics.status_code == 200
    assert metrics.json()["call_aggregation"]["turn_count"] >= 3

    sessions = client.get("/api/calls")
    assert sessions.status_code == 200
    assert any(c["call_id"] == call_id for c in sessions.json())

    # --- RED escalation call ---
    red_call = client.post(
        "/api/calls",
        json={"patient_alias": "Paciente Rojo", "procedure": "apendicectomía"},
    ).json()["call_id"]
    red = client.post(
        f"/api/calls/{red_call}/turns",
        json={"text": "No puedo respirar, me falta el aire mucho."},
    )
    assert red.status_code == 200
    assert red.json()["safety"]["escalate"] is True
    assert red.json()["safety"]["risk"] == "RED"
    client.post(f"/api/calls/{red_call}/finish")
    red_summary = client.get(f"/api/calls/{red_call}/summary")
    assert red_summary.status_code == 200
    assert red_summary.json()["call"]["escalated"] is True
    red_structured = red_summary.json().get("summary") or {}
    if red_structured:
        assert red_structured.get("escalated") is True
        assert (
            red_structured.get("escalation_artifact")
            or red_structured.get("reasons") is not None
        )

    # --- Forget knowledge ---
    deleted = client.delete(f"/api/knowledge/documents/{document_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "REMOVED"

    after = client.get(
        "/api/knowledge/retrieval-probe",
        params={"query": UNIQUE_FACT},
    )
    assert after.status_code == 200
    assert after.json()["chunks"] == []


def test_challenge_profile_rejects_silent_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    from limen.config.challenge_profile import (
        apply_runtime_profile,
        challenge_stub_violations,
    )
    from limen.config.settings import ApplicationSettings

    monkeypatch.setenv("LIMEN_RUNTIME_PROFILE", "challenge")
    for key in (
        "LLM_PROVIDER",
        "STT_PROVIDER",
        "TTS_PROVIDER",
        "EMBEDDING_PROVIDER",
        "LLM_MODEL",
        "STT_MODEL",
        "TTS_VOICE",
        "TTS_MODEL_PATH",
        "STT_DEVICE",
        "STT_COMPUTE_TYPE",
        "APP_ENV",
    ):
        monkeypatch.delenv(key, raising=False)
    apply_runtime_profile(force=True)
    settings = ApplicationSettings(_env_file=None)
    assert settings.llm_provider == "ollama"
    assert settings.stt_provider == "faster_whisper"
    assert settings.tts_provider == "piper"
    assert settings.embedding_provider == "sentence-transformers"
    assert challenge_stub_violations(settings) == []
