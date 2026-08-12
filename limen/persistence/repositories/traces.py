"""SQLite persistence for TRAZA events."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from limen.knowledge.contracts import EvidenceChunk
from limen.persistence.database import Database
from limen.persistence.timeutil import to_text
from limen.tracing.contracts import TRACE_SCHEMA_VERSION, resolve_event_type


class SqliteTraceRepository:
    def __init__(self, database: Database) -> None:
        self._connection = database.connection

    def next_sequence(self, call_id: str) -> int:
        row = self._connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS m FROM trace_events WHERE call_id = ?",
            (call_id,),
        ).fetchone()
        return int(row["m"]) + 1

    def append(
        self,
        *,
        call_id: str,
        account_id: str,
        stage: str,
        label: str,
        detail: str | None = None,
        risk: str | None = None,
        escalate: bool | None = None,
        reasons: list[str] | None = None,
        evidence: list[EvidenceChunk] | None = None,
        metrics: dict[str, Any] | None = None,
        sequence: int | None = None,
        event_type: str | None = None,
        turn_id: str | None = None,
        document_id: str | None = None,
        duration_ms: float | None = None,
        status: str = "ok",
        payload: dict[str, Any] | None = None,
        schema_version: int = TRACE_SCHEMA_VERSION,
    ) -> dict[str, Any]:
        event_id = uuid4().hex
        seq = sequence if sequence is not None else self.next_sequence(call_id)
        stamp = datetime.now(tz=UTC)
        resolved_type = resolve_event_type(stage=stage, event_type=event_type)
        evidence_payload = [
            # Prefer IDs + provenance; truncate text to limit replication.
            # `text` mirrors `text_preview` so the inspector can render citations
            # without a second join to the chunk store.
            {
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "source_name": chunk.source_name,
                "filename": chunk.filename,
                "page": chunk.page,
                "section": chunk.section,
                "score": chunk.score,
                "version": chunk.version,
                "version_id": chunk.version_id,
                "retrieval_modes": list(chunk.retrieval_modes),
                "text": (chunk.text or "")[:160],
                "text_preview": (chunk.text or "")[:160],
            }
            for chunk in (evidence or [])
        ]
        payload_data = payload or {}
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO trace_events (
                    event_id, call_id, account_id, sequence, stage, timestamp,
                    label, detail, risk, escalate, reasons_json, evidence_json,
                    metrics_json, event_type, turn_id, document_id, duration_ms,
                    status, schema_version, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    call_id,
                    account_id,
                    seq,
                    stage,
                    to_text(stamp),
                    label,
                    detail,
                    risk,
                    None if escalate is None else (1 if escalate else 0),
                    json.dumps(reasons or []),
                    json.dumps(evidence_payload),
                    json.dumps(metrics) if metrics is not None else None,
                    resolved_type,
                    turn_id,
                    document_id,
                    duration_ms,
                    status,
                    schema_version,
                    json.dumps(payload_data),
                ),
            )
        return {
            "event_id": event_id,
            "call_id": call_id,
            "sequence": seq,
            "stage": stage,
            "event_type": resolved_type,
            "schema_version": schema_version,
            "timestamp": stamp.isoformat(),
            "label": label,
            "detail": detail,
            "risk": risk,
            "escalate": escalate,
            "reasons": reasons or [],
            "evidence": evidence_payload,
            "metrics": metrics,
            "turn_id": turn_id,
            "document_id": document_id,
            "duration_ms": duration_ms,
            "status": status,
            "payload": payload_data,
        }

    def list_events(self, account_id: str, call_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT * FROM trace_events
            WHERE account_id = ? AND call_id = ?
            ORDER BY sequence ASC
            """,
            (account_id, call_id),
        ).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            escalate = row["escalate"]
            keys = set(row.keys())
            events.append(
                {
                    "event_id": row["event_id"],
                    "call_id": row["call_id"],
                    "sequence": row["sequence"],
                    "stage": row["stage"],
                    "event_type": row["event_type"]
                    if "event_type" in keys and row["event_type"]
                    else resolve_event_type(stage=row["stage"]),
                    "schema_version": int(row["schema_version"])
                    if "schema_version" in keys and row["schema_version"] is not None
                    else TRACE_SCHEMA_VERSION,
                    "timestamp": row["timestamp"],
                    "label": row["label"],
                    "detail": row["detail"],
                    "risk": row["risk"],
                    "escalate": None if escalate is None else bool(escalate),
                    "reasons": json.loads(row["reasons_json"] or "[]"),
                    "evidence": json.loads(row["evidence_json"] or "[]"),
                    "metrics": json.loads(row["metrics_json"]) if row["metrics_json"] else None,
                    "turn_id": row["turn_id"] if "turn_id" in keys else None,
                    "document_id": row["document_id"] if "document_id" in keys else None,
                    "duration_ms": row["duration_ms"] if "duration_ms" in keys else None,
                    "status": row["status"] if "status" in keys else "ok",
                    "payload": json.loads(row["payload_json"] or "{}")
                    if "payload_json" in keys
                    else {},
                }
            )
        return events
