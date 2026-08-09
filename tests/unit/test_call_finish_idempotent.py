"""CallService.finish must be idempotent across server+client hang-up."""

from __future__ import annotations

from pathlib import Path

from limen.conversation.call_service import CallService
from limen.persistence.database import Database
from limen.persistence.repositories.calls import SqliteCallRepository
from limen.persistence.repositories.traces import SqliteTraceRepository


def test_finish_twice_does_not_duplicate_session_end_trace(tmp_path: Path) -> None:
    db = Database(tmp_path / "finish.db")
    db.initialize()
    calls = SqliteCallRepository(db)
    traces = SqliteTraceRepository(db)
    service = CallService(calls=calls, traces=traces)

    account_id = "acct-finish"
    db.connection.execute(
        "INSERT INTO accounts (account_id, email, password_hash, display_name, created_at) "
        "VALUES (?, ?, ?, ?, datetime('now'))",
        (account_id, "finish@test.local", "x", "Finish Test"),
    )
    db.connection.commit()

    created = service.create(account_id=account_id, patient_alias="Paciente")
    call_id = created["call_id"]

    first = service.finish(account_id=account_id, call_id=call_id)
    second = service.finish(account_id=account_id, call_id=call_id)

    assert first is not None
    assert second is not None
    assert first["call_id"] == call_id
    assert second["call_id"] == call_id
    assert first.get("duration_seconds") is not None
    assert second.get("duration_seconds") is not None

    events = traces.list_events(account_id, call_id)
    session_ends = [e for e in events if e.get("event_type") == "call.completed"]
    assert len(session_ends) == 1
