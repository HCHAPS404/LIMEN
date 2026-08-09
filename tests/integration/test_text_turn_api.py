"""HTTP text-turn contract, TRAZA ordering, and persistence."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from limen.clinical.state import ClinicalState, Finding
from limen.clinical.uncertainty import ClinicalCertainty
from limen.config import settings as settings_module
from limen.persistence.database import get_database, reset_database_for_tests
from limen.persistence.repositories.calls import SqliteCallRepository

PASSWORD = "umbral-seguro-2026"

_TURN_STAGES = (
    "patient_statement",
    "clinical_extraction",
    "uncertainty",
    "retrieval",
    "safety_evaluation",
    "response",
)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "text_turn.db"))
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
            "email": "turno@umbral.io",
            "password": PASSWORD,
            "display_name": "Turno Text",
        },
    )
    assert response.status_code == 201, response.text


def test_post_text_turn_returns_typed_payload_and_persists_traza(client: TestClient) -> None:
    _register(client)
    created = client.post(
        "/api/calls",
        json={"patient_alias": "Paciente T", "procedure": "hernia", "postoperative_day": 1},
    )
    assert created.status_code == 201
    call_id = created.json()["call_id"]

    turn = client.post(
        f"/api/calls/{call_id}/turns",
        json={"text": "tengo fiebre y un poco de dolor"},
    )
    assert turn.status_code == 200, turn.text
    body = turn.json()
    assert body["assistant_text"]
    assert isinstance(body["clinical_state"]["findings"], list)
    assert all("certainty" in finding for finding in body["clinical_state"]["findings"])
    assert body["safety"]["risk"] in {"GREEN", "YELLOW", "ORANGE", "RED"}
    assert "escalate" in body["safety"]
    assert "reasons" in body["safety"]
    assert "policy_version" in body["safety"]
    assert isinstance(body["evidence"], list)
    assert "latency_ms" in body["metrics"]
    assert body["metrics"]["estimated_cost_usd"] is None

    trace = client.get(f"/api/traces/{call_id}")
    assert trace.status_code == 200
    events = trace.json()["events"]
    stages = [event["stage"] for event in events]
    for required in _TURN_STAGES:
        assert required in stages, stages

    # First occurrence of each required stage must be monotonically ordered.
    first_seq: dict[str, int] = {}
    for event in events:
        stage = event["stage"]
        if stage in _TURN_STAGES and stage not in first_seq:
            first_seq[stage] = event["sequence"]
    ordered = [first_seq[stage] for stage in _TURN_STAGES]
    assert ordered == sorted(ordered)

    event_types = [event.get("event_type") for event in events]
    assert "response.generation.started" in event_types
    assert "response.generation.completed" in event_types
    # Stub GREEN/YELLOW path may validate; fallback event is optional but allowed.
    assert "safety.evaluation.completed" in event_types


def test_post_text_turn_persists_turns_state_safety_and_reasons(client: TestClient) -> None:
    _register(client)
    created = client.post("/api/calls", json={"patient_alias": "Paciente P"})
    call_id = created.json()["call_id"]
    user_text = "tengo fiebre"

    turn = client.post(f"/api/calls/{call_id}/turns", json={"text": user_text})
    assert turn.status_code == 200, turn.text
    body = turn.json()
    assert body["safety"]["risk"] == "YELLOW"
    assert body["safety"]["reasons"]
    assert any(f["name"] == "fever" for f in body["clinical_state"]["findings"])

    summary = client.get(f"/api/calls/{call_id}/summary")
    assert summary.status_code == 200
    payload = summary.json()
    speakers = [t["speaker"] for t in payload["turns"]]
    texts = [t["text"] for t in payload["turns"]]
    assert "patient" in speakers
    assert "agent" in speakers
    assert user_text in texts
    assert body["assistant_text"] in texts
    assert any(f["name"] == "fever" for f in payload["clinical_state"]["findings"])
    assert payload["call"]["final_risk"] == "YELLOW"
    assert payload["call"]["escalated"] is False

    events = client.get(f"/api/traces/{call_id}").json()["events"]
    safety_events = [e for e in events if e["stage"] == "safety_evaluation"]
    assert safety_events
    assert safety_events[0]["risk"] == "YELLOW"
    assert safety_events[0]["reasons"]
    assert any(e["stage"] == "patient_statement" for e in events)
    assert any(e["stage"] == "response" for e in events)


def test_post_text_turn_escalation_persists_escalation_stage(client: TestClient) -> None:
    _register(client)
    created = client.post("/api/calls", json={"patient_alias": "Paciente R"})
    call_id = created.json()["call_id"]

    turn = client.post(
        f"/api/calls/{call_id}/turns",
        json={"text": "no puedo respirar y hay sangrado abundante"},
    )
    assert turn.status_code == 200, turn.text
    body = turn.json()
    assert body["safety"]["escalate"] is True
    assert body["safety"]["risk"] == "RED"
    assistant = body["assistant_text"].lower()
    assert "urgencia" in assistant or "médica" in assistant

    stages = [event["stage"] for event in client.get(f"/api/traces/{call_id}").json()["events"]]
    assert "escalation" in stages
    # Escalation follows response in sequence.
    events = client.get(f"/api/traces/{call_id}").json()["events"]
    by_stage = {e["stage"]: e["sequence"] for e in events}
    assert by_stage["response"] < by_stage["escalation"]


def test_escalation_and_red_risk_stay_sticky_after_benign_turn(
    client: TestClient,
) -> None:
    """Call-level escalated/final_risk must not clear on a later GREEN turn."""
    _register(client)
    created = client.post("/api/calls", json={"patient_alias": "Paciente Sticky"})
    call_id = created.json()["call_id"]

    red = client.post(
        f"/api/calls/{call_id}/turns",
        json={"text": "no puedo respirar y hay sangrado abundante"},
    )
    assert red.status_code == 200, red.text
    assert red.json()["safety"]["escalate"] is True
    assert red.json()["safety"]["risk"] == "RED"

    benign = client.post(
        f"/api/calls/{call_id}/turns",
        json={"text": "ahora solo me duele un poco la cabeza"},
    )
    assert benign.status_code == 200, benign.text
    # Turn-level safety may be lower; call-level must remain sticky RED.
    assert benign.json()["safety"]["risk"] in {"GREEN", "YELLOW", "ORANGE", "RED"}

    summary = client.get(f"/api/calls/{call_id}/summary")
    assert summary.status_code == 200, summary.text
    call_body = summary.json()["call"]
    assert call_body["escalated"] is True
    assert call_body["final_risk"] == "RED"


def test_conflicting_state_survives_http_turn(client: TestClient) -> None:
    _register(client)
    created = client.post("/api/calls", json={"patient_alias": "Paciente C"})
    call_id = created.json()["call_id"]

    # Seed CONFLICTING via persistence (extraction does not invent CONFLICTING).
    settings = settings_module.get_settings()
    db = get_database(settings)
    calls = SqliteCallRepository(db)
    account_id = _account_id_for_call(db, call_id)
    seeded = ClinicalState(
        findings=[
            Finding(name="wound", certainty=ClinicalCertainty.CONFLICTING, notes="mixed reports"),
        ]
    )
    calls.update_runtime(
        account_id=account_id,
        call_id=call_id,
        clinical_state=seeded,
        final_risk=None,
        escalated=False,
    )

    turn = client.post(
        f"/api/calls/{call_id}/turns",
        json={"text": "sigo con dudas sobre la herida"},
    )
    assert turn.status_code == 200, turn.text
    body = turn.json()
    wound = next(f for f in body["clinical_state"]["findings"] if f["name"] == "wound")
    assert wound["certainty"] == "CONFLICTING"
    assert any("herida" in q.lower() for q in body["clinical_state"]["open_questions"])


def test_post_text_turn_on_finished_call_conflicts(client: TestClient) -> None:
    _register(client)
    created = client.post("/api/calls", json={"patient_alias": "Paciente F"})
    call_id = created.json()["call_id"]
    assert client.post(f"/api/calls/{call_id}/finish").status_code == 200
    turn = client.post(f"/api/calls/{call_id}/turns", json={"text": "hola"})
    assert turn.status_code == 409


def _account_id_for_call(db, call_id: str) -> str:
    row = db.connection.execute(
        "SELECT account_id FROM calls WHERE call_id = ?",
        (call_id,),
    ).fetchone()
    assert row is not None
    return str(row["account_id"])
