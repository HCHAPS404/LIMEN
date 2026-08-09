"""PHASE 6 WebSocket voice path with stub STT/TTS."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from limen.config import settings as settings_module
from limen.persistence.database import reset_database_for_tests
from limen.voice.audio_codec import silence_wav

PASSWORD = "umbral-seguro-2026"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "voice.db"))
    monkeypatch.setenv("DOCUMENT_PATH", str(tmp_path / "documents"))
    monkeypatch.setenv("VECTOR_PATH", str(tmp_path / "vectors"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STT_PROVIDER", "stub")
    monkeypatch.setenv("TTS_PROVIDER", "stub")
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
            "email": "voice@umbral.io",
            "password": PASSWORD,
            "display_name": "Voice User",
        },
    )
    assert response.status_code == 201, response.text


def test_websocket_binary_stub_stt_tts_yellow_path(client: TestClient) -> None:
    _register(client)
    created = client.post("/api/calls", json={"patient_alias": "Paciente V"})
    assert created.status_code == 201
    call_id = created.json()["call_id"]

    with client.websocket_connect(f"/api/calls/{call_id}/stream") as ws:
        first = ws.receive_json()
        assert first["type"] == "call.state"
        assert first["payload"]["state"] == "LISTENING"

        ws.send_json({"type": "voice.speech.ended", "speech_end_monotonic": 10.0})
        ws.send_bytes(silence_wav(duration_ms=400))

        events = []
        audio_frames = 0
        # Drain until LISTENING after SPEAKING or error.
        for _ in range(40):
            message = ws.receive()
            if message.get("bytes") is not None:
                audio_frames += 1
                assert message["bytes"][:4] == b"RIFF"
                continue
            event = json.loads(message["text"])
            events.append(event)
            if (
                event["type"] == "call.state"
                and event["payload"].get("state") == "LISTENING"
                and any(e["type"] == "call.transcript" for e in events)
            ):
                break

        types = [e["type"] for e in events]
        assert "call.transcript" in types
        assert "call.safety" in types
        assert audio_frames >= 1

        # Simulate browser playback ack for latency sample.
        turn_seq = next(
            (e["payload"].get("turn_seq") for e in events if e["type"] == "call.audio"),
            1,
        )
        ws.send_json(
            {
                "type": "voice.playback.started",
                "turn_seq": turn_seq,
                "agent_audio_started_monotonic": 10.8,
            }
        )
        # May receive metrics event
        for _ in range(5):
            try:
                msg = ws.receive_json()
            except Exception:  # noqa: BLE001
                break
            if msg["type"] == "call.metrics" and "voice_response_latency_ms" in msg["payload"]:
                assert msg["payload"]["voice_response_latency_ms"] == pytest.approx(800.0)
                break

        ws.send_json({"type": "end"})


def test_websocket_red_escalation_uses_template_path(client: TestClient) -> None:
    _register(client)
    created = client.post("/api/calls", json={"patient_alias": "Paciente R"})
    call_id = created.json()["call_id"]
    with client.websocket_connect(f"/api/calls/{call_id}/stream") as ws:
        ws.receive_json()
        ws.send_json({"type": "text", "text": "no puedo respirar"})
        saw_red = False
        saw_ended = False
        for _ in range(30):
            message = ws.receive()
            if message.get("bytes") is not None:
                continue
            event = json.loads(message["text"])
            if event["type"] == "call.safety":
                assert event["payload"]["risk"] == "RED"
                assert event["payload"]["escalate"] is True
                saw_red = True
            if event["type"] == "call.ended":
                saw_ended = True
                break
        assert saw_red and saw_ended


def test_websocket_interrupt_does_not_crash(client: TestClient) -> None:
    _register(client)
    created = client.post("/api/calls", json={"patient_alias": "Paciente I"})
    call_id = created.json()["call_id"]
    with client.websocket_connect(f"/api/calls/{call_id}/stream") as ws:
        ws.receive_json()
        ws.send_json({"type": "voice.interrupt"})
        event = ws.receive_json()
        assert event["type"] == "call.state"
        assert event["payload"]["state"] in {"INTERRUPTED", "LISTENING"}


def test_unauthenticated_websocket_denied(client: TestClient) -> None:
    client.cookies.clear()
    with client.websocket_connect("/api/calls/missing/stream") as ws:
        event = ws.receive_json()
        assert event["type"] == "call.error"
        assert event["payload"]["code"] in {"session_invalid", "call_not_found"}
