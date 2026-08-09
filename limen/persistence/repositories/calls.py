"""SQLite persistence for calls, turns, and structured summaries."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from limen.clinical.state import ClinicalState
from limen.persistence.database import Database
from limen.persistence.timeutil import from_text, to_text
from limen.safety.decision import Severity


class SqliteCallRepository:
    def __init__(self, database: Database) -> None:
        self._connection = database.connection

    def create_call(
        self,
        *,
        account_id: str,
        patient_alias: str,
        procedure: str | None = None,
        postoperative_day: int | None = None,
    ) -> dict[str, Any]:
        call_id = uuid4().hex
        started = datetime.now(tz=UTC)
        clinical = ClinicalState().model_dump(mode="json")
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO calls (
                    call_id, account_id, patient_alias, procedure, postoperative_day,
                    started_at, escalated, clinical_state_json, metrics_json
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, '{}')
                """,
                (
                    call_id,
                    account_id,
                    patient_alias,
                    procedure,
                    postoperative_day,
                    to_text(started),
                    json.dumps(clinical),
                ),
            )
        return self.get_call(account_id, call_id)  # type: ignore[return-value]

    def list_calls(self, account_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT * FROM calls WHERE account_id = ?
            ORDER BY started_at DESC
            """,
            (account_id,),
        ).fetchall()
        return [self._to_summary(row) for row in rows]

    def get_call(self, account_id: str, call_id: str) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT * FROM calls WHERE account_id = ? AND call_id = ?",
            (account_id, call_id),
        ).fetchone()
        return None if row is None else self._to_summary(row)

    def get_call_row(self, account_id: str, call_id: str) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT * FROM calls WHERE account_id = ? AND call_id = ?",
            (account_id, call_id),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def finish_call(
        self,
        *,
        account_id: str,
        call_id: str,
        final_risk: str | None,
        escalated: bool,
        summary: dict[str, Any],
        clinical_state: ClinicalState,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        row = self.get_call_row(account_id, call_id)
        if row is None:
            return None
        started = from_text(row["started_at"])
        ended = datetime.now(tz=UTC)
        duration = max(0, int((ended - started).total_seconds()))
        with self._connection:
            self._connection.execute(
                """
                UPDATE calls SET
                    ended_at = ?,
                    duration_seconds = ?,
                    final_risk = ?,
                    escalated = ?,
                    summary_json = ?,
                    clinical_state_json = ?,
                    metrics_json = ?
                WHERE account_id = ? AND call_id = ?
                """,
                (
                    to_text(ended),
                    duration,
                    final_risk,
                    1 if escalated else 0,
                    json.dumps(summary),
                    clinical_state.model_dump_json(),
                    json.dumps(metrics or json.loads(row["metrics_json"] or "{}")),
                    account_id,
                    call_id,
                ),
            )
        return self.get_call(account_id, call_id)

    def update_runtime(
        self,
        *,
        account_id: str,
        call_id: str,
        clinical_state: ClinicalState,
        final_risk: str | None,
        escalated: bool,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        with self._connection:
            self._connection.execute(
                """
                UPDATE calls SET
                    clinical_state_json = ?,
                    final_risk = ?,
                    escalated = ?,
                    metrics_json = COALESCE(?, metrics_json)
                WHERE account_id = ? AND call_id = ?
                """,
                (
                    clinical_state.model_dump_json(),
                    final_risk,
                    1 if escalated else 0,
                    json.dumps(metrics) if metrics is not None else None,
                    account_id,
                    call_id,
                ),
            )

    def append_turn(
        self,
        *,
        call_id: str,
        speaker: str,
        text: str,
        interrupted: bool = False,
    ) -> dict[str, Any]:
        sequence = self._next_turn_sequence(call_id)
        turn_id = uuid4().hex
        stamp = datetime.now(tz=UTC)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO call_turns (
                    turn_id, call_id, sequence, speaker, text, timestamp, interrupted
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn_id,
                    call_id,
                    sequence,
                    speaker,
                    text,
                    to_text(stamp),
                    1 if interrupted else 0,
                ),
            )
        return {
            "turn_id": turn_id,
            "speaker": speaker,
            "text": text,
            "timestamp": stamp.isoformat(),
            "interrupted": interrupted,
        }

    def list_turns(self, call_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT * FROM call_turns WHERE call_id = ?
            ORDER BY sequence ASC
            """,
            (call_id,),
        ).fetchall()
        return [
            {
                "turn_id": row["turn_id"],
                "speaker": row["speaker"],
                "text": row["text"],
                "timestamp": row["timestamp"],
                "interrupted": bool(row["interrupted"]),
            }
            for row in rows
        ]

    def get_summary_payload(self, account_id: str, call_id: str) -> dict[str, Any] | None:
        row = self.get_call_row(account_id, call_id)
        if row is None:
            return None
        summary = json.loads(row["summary_json"]) if row["summary_json"] else None
        clinical = ClinicalState.model_validate_json(row["clinical_state_json"] or "{}")
        metrics = json.loads(row["metrics_json"] or "{}")
        return {
            "call": self._to_summary(row),
            "summary": summary,
            "clinical_state": clinical.model_dump(mode="json"),
            "metrics": metrics,
            "turns": self.list_turns(call_id),
        }

    def load_clinical_state(self, account_id: str, call_id: str) -> ClinicalState:
        row = self.get_call_row(account_id, call_id)
        if row is None:
            return ClinicalState()
        return ClinicalState.model_validate_json(row["clinical_state_json"] or "{}")

    def _next_turn_sequence(self, call_id: str) -> int:
        row = self._connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS m FROM call_turns WHERE call_id = ?",
            (call_id,),
        ).fetchone()
        return int(row["m"]) + 1

    def _to_summary(self, row: Any) -> dict[str, Any]:
        risk = row["final_risk"]
        if risk is not None and risk not in {s.name for s in Severity}:
            risk = None
        return {
            "call_id": row["call_id"],
            "patient_alias": row["patient_alias"],
            "procedure": row["procedure"],
            "postoperative_day": row["postoperative_day"],
            "started_at": row["started_at"],
            "duration_seconds": row["duration_seconds"],
            "final_risk": risk,
            "escalated": bool(row["escalated"]),
        }
