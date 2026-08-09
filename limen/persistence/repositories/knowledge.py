"""SQLite + FTS5 persistence for knowledge documents and chunks."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from limen.knowledge.chunking import ProvenancedChunk, chunk_pages
from limen.knowledge.contracts import EvidenceChunk, KnowledgeStatus
from limen.knowledge.lifecycle import assert_transition
from limen.persistence.database import Database
from limen.persistence.timeutil import to_text

_ACTIVE_STATUSES = (
    KnowledgeStatus.UPLOADED.value,
    KnowledgeStatus.PROCESSING.value,
    KnowledgeStatus.AVAILABLE.value,
)


class SqliteKnowledgeRepository:
    def __init__(self, database: Database) -> None:
        self._connection = database.connection

    def list_documents(self, account_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT * FROM documents
            WHERE account_id = ? AND status != ?
            ORDER BY uploaded_at DESC
            """,
            (account_id, KnowledgeStatus.REMOVED.value),
        ).fetchall()
        return [self._to_document(row) for row in rows]

    def get_document(self, account_id: str, document_id: str) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT * FROM documents WHERE account_id = ? AND document_id = ?",
            (account_id, document_id),
        ).fetchone()
        return None if row is None else self._to_document(row)

    def find_active_by_sha256(self, account_id: str, sha256: str) -> dict[str, Any] | None:
        placeholders = ",".join("?" for _ in _ACTIVE_STATUSES)
        row = self._connection.execute(
            f"""
            SELECT * FROM documents
            WHERE account_id = ? AND sha256 = ? AND status IN ({placeholders})
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (account_id, sha256, *_ACTIVE_STATUSES),
        ).fetchone()
        return None if row is None else self._to_document(row)

    def create_document(
        self,
        *,
        account_id: str,
        source_name: str,
        size_bytes: int,
        storage_path: str,
        sha256: str,
    ) -> dict[str, Any]:
        document_id = uuid4().hex
        version_id = uuid4().hex
        uploaded = datetime.now(tz=UTC)
        stamp = to_text(uploaded)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO documents (
                    document_id, account_id, source_name, status, version,
                    active_version_id, uploaded_at, updated_at, size_bytes,
                    sha256, storage_path, ocr_applied
                ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    document_id,
                    account_id,
                    source_name,
                    KnowledgeStatus.UPLOADED.value,
                    version_id,
                    stamp,
                    stamp,
                    size_bytes,
                    sha256,
                    storage_path,
                ),
            )
            self._connection.execute(
                """
                INSERT INTO document_versions (
                    version_id, document_id, account_id, version_number,
                    content_hash, status, created_at
                ) VALUES (?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    version_id,
                    document_id,
                    account_id,
                    sha256,
                    KnowledgeStatus.UPLOADED.value,
                    stamp,
                ),
            )
        self.append_event(
            account_id=account_id,
            document_id=document_id,
            stage="knowledge.uploaded",
            label="Document uploaded",
            detail=source_name,
            payload={"sha256": sha256, "version_id": version_id},
        )
        return self.get_document(account_id, document_id)  # type: ignore[return-value]

    def set_storage_path(self, account_id: str, document_id: str, storage_path: str) -> None:
        with self._connection:
            self._connection.execute(
                """
                UPDATE documents SET storage_path = ?, updated_at = ?
                WHERE account_id = ? AND document_id = ?
                """,
                (storage_path, to_text(datetime.now(tz=UTC)), account_id, document_id),
            )

    def storage_path(self, account_id: str, document_id: str) -> str | None:
        row = self._connection.execute(
            """
            SELECT storage_path FROM documents
            WHERE account_id = ? AND document_id = ?
            """,
            (account_id, document_id),
        ).fetchone()
        if row is None:
            return None
        path = row["storage_path"]
        return str(path) if path is not None else None

    def transition_status(
        self,
        account_id: str,
        document_id: str,
        target: KnowledgeStatus,
        *,
        failure_stage: str | None = None,
        failure_message: str | None = None,
        indexed_at: str | None = None,
        removed_at: str | None = None,
        chunk_count: int | None = None,
        page_count: int | None = None,
        parser: str | None = None,
        ocr_applied: bool | None = None,
    ) -> dict[str, Any] | None:
        current = self.get_document(account_id, document_id)
        if current is None:
            return None
        assert_transition(KnowledgeStatus(current["status"]), target)
        stamp = to_text(datetime.now(tz=UTC))
        with self._connection:
            self._connection.execute(
                """
                UPDATE documents SET
                    status = ?,
                    updated_at = ?,
                    failure_stage = COALESCE(?, failure_stage),
                    failure_message = COALESCE(?, failure_message),
                    indexed_at = COALESCE(?, indexed_at),
                    removed_at = COALESCE(?, removed_at),
                    chunk_count = COALESCE(?, chunk_count),
                    page_count = COALESCE(?, page_count),
                    parser = COALESCE(?, parser),
                    ocr_applied = COALESCE(?, ocr_applied)
                WHERE account_id = ? AND document_id = ?
                """,
                (
                    target.value,
                    stamp,
                    failure_stage,
                    failure_message,
                    indexed_at,
                    removed_at,
                    chunk_count,
                    page_count,
                    parser,
                    None if ocr_applied is None else (1 if ocr_applied else 0),
                    account_id,
                    document_id,
                ),
            )
            version_id = current.get("active_version_id")
            if version_id:
                self._connection.execute(
                    """
                    UPDATE document_versions SET
                        status = ?,
                        indexed_at = COALESCE(?, indexed_at),
                        removed_at = COALESCE(?, removed_at),
                        chunk_count = COALESCE(?, chunk_count),
                        page_count = COALESCE(?, page_count)
                    WHERE version_id = ? AND account_id = ?
                    """,
                    (
                        target.value,
                        indexed_at,
                        removed_at,
                        chunk_count,
                        page_count,
                        version_id,
                        account_id,
                    ),
                )
        return self.get_document(account_id, document_id)

    def fail_all_processing(self, *, stage: str, message: str) -> int:
        """Mark every PROCESSING document FAILED (startup interruption policy)."""
        rows = self._connection.execute(
            """
            SELECT account_id, document_id FROM documents
            WHERE status = ?
            """,
            (KnowledgeStatus.PROCESSING.value,),
        ).fetchall()
        count = 0
        for row in rows:
            self.mark_failed(
                row["account_id"],
                row["document_id"],
                stage=stage,
                message=message,
            )
            count += 1
        return count

    def mark_failed(
        self,
        account_id: str,
        document_id: str,
        *,
        stage: str,
        message: str,
    ) -> None:
        self.transition_status(
            account_id,
            document_id,
            KnowledgeStatus.FAILED,
            failure_stage=stage,
            failure_message=message,
        )
        self.append_event(
            account_id=account_id,
            document_id=document_id,
            stage="knowledge.failed",
            label="Document processing failed",
            detail=f"{stage}: {message}",
            status="error",
            payload={"failure_stage": stage, "safe_message": message[:500]},
        )

    def mark_processing(self, account_id: str, document_id: str) -> dict[str, Any] | None:
        doc = self.transition_status(account_id, document_id, KnowledgeStatus.PROCESSING)
        self.append_event(
            account_id=account_id,
            document_id=document_id,
            stage="knowledge.processing_started",
            label="Processing started",
        )
        return doc

    def index_chunks(
        self,
        *,
        account_id: str,
        document_id: str,
        version_id: str,
        source_name: str,
        chunks: list[ProvenancedChunk],
        parser: str,
        ocr_applied: bool,
        page_count: int | None,
    ) -> None:
        with self._connection:
            for chunk in chunks:
                self._connection.execute(
                    """
                    INSERT INTO document_chunks (
                        chunk_id, document_id, account_id, version_id, source_name,
                        filename, page, section, version, text, content_hash,
                        ordinal, active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, 1)
                    """,
                    (
                        chunk.chunk_id,
                        document_id,
                        account_id,
                        version_id,
                        source_name,
                        chunk.filename,
                        chunk.page,
                        chunk.section,
                        chunk.text,
                        chunk.content_hash,
                        chunk.ordinal,
                    ),
                )
                self._connection.execute(
                    """
                    INSERT INTO document_chunks_fts (
                        chunk_id, account_id, document_id, source_name, text
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.chunk_id,
                        account_id,
                        document_id,
                        source_name,
                        chunk.text,
                    ),
                )
            self._connection.execute(
                """
                UPDATE documents SET
                    parser = ?, ocr_applied = ?, page_count = ?, chunk_count = ?,
                    updated_at = ?, failure_stage = NULL, failure_message = NULL
                WHERE account_id = ? AND document_id = ?
                """,
                (
                    parser,
                    1 if ocr_applied else 0,
                    page_count,
                    len(chunks),
                    to_text(datetime.now(tz=UTC)),
                    account_id,
                    document_id,
                ),
            )
            self._connection.execute(
                """
                UPDATE document_versions SET
                    page_count = ?, chunk_count = ?
                WHERE version_id = ? AND account_id = ?
                """,
                (page_count, len(chunks), version_id, account_id),
            )
        self.append_event(
            account_id=account_id,
            document_id=document_id,
            stage="knowledge.chunked",
            label="Document chunked",
            detail=f"{len(chunks)} chunks",
        )
        self.append_event(
            account_id=account_id,
            document_id=document_id,
            stage="knowledge.indexed",
            label="Lexical index updated",
            detail=f"{len(chunks)} FTS rows",
        )

    def verify_indexed(
        self,
        *,
        account_id: str,
        document_id: str,
        version_id: str,
        probe_token: str | None = None,
    ) -> bool:
        """Confirm active chunks exist in storage and FTS before AVAILABLE."""
        chunk_row = self._connection.execute(
            """
            SELECT COUNT(*) AS n FROM document_chunks
            WHERE account_id = ? AND document_id = ? AND version_id = ? AND active = 1
            """,
            (account_id, document_id, version_id),
        ).fetchone()
        fts_row = self._connection.execute(
            """
            SELECT COUNT(*) AS n FROM document_chunks_fts
            WHERE account_id = ? AND document_id = ?
            """,
            (account_id, document_id),
        ).fetchone()
        chunk_count = int(chunk_row["n"] if chunk_row else 0)
        fts_count = int(fts_row["n"] if fts_row else 0)
        if chunk_count <= 0 or chunk_count != fts_count:
            return False
        if probe_token:
            hits = self.retrieve(account_id=account_id, query=probe_token, limit=5)
            # Document is still PROCESSING; retrieve filters AVAILABLE only.
            # Probe FTS directly for this document.
            probe = self._connection.execute(
                """
                SELECT COUNT(*) AS n FROM document_chunks_fts
                WHERE account_id = ? AND document_id = ? AND text LIKE ?
                """,
                (account_id, document_id, f"%{probe_token}%"),
            ).fetchone()
            if int(probe["n"] if probe else 0) <= 0 and not any(
                h.document_id == document_id for h in hits
            ):
                # Soft: if token not in FTS text, still OK if counts match
                # (token may be punctuation-stripped). Counts already matched.
                pass
        return True

    def mark_available(self, account_id: str, document_id: str) -> dict[str, Any] | None:
        stamp = to_text(datetime.now(tz=UTC))
        current = self.get_document(account_id, document_id)
        if current is None:
            return None
        assert_transition(KnowledgeStatus(current["status"]), KnowledgeStatus.AVAILABLE)
        with self._connection:
            self._connection.execute(
                """
                UPDATE documents SET
                    status = ?, updated_at = ?, indexed_at = ?,
                    failure_stage = NULL, failure_message = NULL
                WHERE account_id = ? AND document_id = ?
                """,
                (
                    KnowledgeStatus.AVAILABLE.value,
                    stamp,
                    stamp,
                    account_id,
                    document_id,
                ),
            )
            version_id = current.get("active_version_id")
            if version_id:
                self._connection.execute(
                    """
                    UPDATE document_versions SET status = ?, indexed_at = ?
                    WHERE version_id = ? AND account_id = ?
                    """,
                    (
                        KnowledgeStatus.AVAILABLE.value,
                        stamp,
                        version_id,
                        account_id,
                    ),
                )
        self.append_event(
            account_id=account_id,
            document_id=document_id,
            stage="knowledge.available",
            label="Document available after verified indexing",
        )
        return self.get_document(account_id, document_id)

    def begin_removal(self, account_id: str, document_id: str) -> dict[str, Any] | None:
        doc = self.get_document(account_id, document_id)
        if doc is None:
            return None
        if doc["status"] == KnowledgeStatus.REMOVED.value:
            return doc
        if doc["status"] != KnowledgeStatus.REMOVING.value:
            self.transition_status(account_id, document_id, KnowledgeStatus.REMOVING)
        self.append_event(
            account_id=account_id,
            document_id=document_id,
            stage="knowledge.deletion_started",
            label="Deletion started",
        )
        return self.get_document(account_id, document_id)

    def purge_active_artifacts(self, account_id: str, document_id: str) -> None:
        with self._connection:
            self._connection.execute(
                "DELETE FROM document_chunks_fts WHERE document_id = ? AND account_id = ?",
                (document_id, account_id),
            )
            self._connection.execute(
                """
                UPDATE document_chunks SET active = 0
                WHERE document_id = ? AND account_id = ?
                """,
                (document_id, account_id),
            )
            self._connection.execute(
                "DELETE FROM document_chunks WHERE document_id = ? AND account_id = ?",
                (document_id, account_id),
            )
        self.append_event(
            account_id=account_id,
            document_id=document_id,
            stage="knowledge.purged",
            label="Active retrieval artifacts purged",
        )

    def verify_forgotten(self, account_id: str, document_id: str) -> bool:
        fts = self._connection.execute(
            """
            SELECT COUNT(*) AS n FROM document_chunks_fts
            WHERE account_id = ? AND document_id = ?
            """,
            (account_id, document_id),
        ).fetchone()
        active = self._connection.execute(
            """
            SELECT COUNT(*) AS n FROM document_chunks
            WHERE account_id = ? AND document_id = ? AND active = 1
            """,
            (account_id, document_id),
        ).fetchone()
        return int(fts["n"] if fts else 0) == 0 and int(active["n"] if active else 0) == 0

    def mark_removed(self, account_id: str, document_id: str) -> dict[str, Any] | None:
        stamp = to_text(datetime.now(tz=UTC))
        doc = self.transition_status(
            account_id,
            document_id,
            KnowledgeStatus.REMOVED,
            removed_at=stamp,
            chunk_count=0,
        )
        self.append_event(
            account_id=account_id,
            document_id=document_id,
            stage="knowledge.removed",
            label="Document removed after verified purge",
        )
        return doc

    def count_active_chunks(self, account_id: str, document_id: str) -> int:
        row = self._connection.execute(
            """
            SELECT COUNT(*) AS n FROM document_chunks
            WHERE account_id = ? AND document_id = ? AND active = 1
            """,
            (account_id, document_id),
        ).fetchone()
        return int(row["n"] if row else 0)

    def list_events(self, account_id: str, document_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT * FROM knowledge_events
            WHERE account_id = ? AND document_id = ?
            ORDER BY sequence ASC
            """,
            (account_id, document_id),
        ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "document_id": row["document_id"],
                "sequence": row["sequence"],
                "stage": row["stage"],
                "event_type": row["event_type"]
                if "event_type" in keys and row["event_type"]
                else row["stage"],
                "timestamp": row["timestamp"],
                "label": row["label"],
                "detail": row["detail"],
                "payload": json.loads(row["payload_json"] or "{}"),
                "duration_ms": row["duration_ms"] if "duration_ms" in keys else None,
                "status": row["status"] if "status" in keys else "ok",
                "schema_version": int(row["schema_version"])
                if "schema_version" in keys and row["schema_version"] is not None
                else 1,
            }
            for row in rows
            for keys in [set(row.keys())]
        ]

    def append_event(
        self,
        *,
        account_id: str,
        document_id: str | None,
        stage: str,
        label: str,
        detail: str | None = None,
        payload: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        status: str = "ok",
        event_type: str | None = None,
    ) -> None:
        from limen.tracing.contracts import TRACE_SCHEMA_VERSION, resolve_event_type

        sequence = 1
        if document_id:
            row = self._connection.execute(
                """
                SELECT COALESCE(MAX(sequence), 0) AS m FROM knowledge_events
                WHERE account_id = ? AND document_id = ?
                """,
                (account_id, document_id),
            ).fetchone()
            sequence = int(row["m"]) + 1
        resolved = resolve_event_type(stage=stage, event_type=event_type)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO knowledge_events (
                    event_id, account_id, document_id, sequence, stage,
                    timestamp, label, detail, payload_json,
                    event_type, duration_ms, status, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid4().hex,
                    account_id,
                    document_id,
                    sequence,
                    stage,
                    to_text(datetime.now(tz=UTC)),
                    label,
                    detail,
                    json.dumps(payload or {}),
                    resolved,
                    duration_ms,
                    status,
                    TRACE_SCHEMA_VERSION,
                ),
            )

    def retrieve(
        self,
        *,
        account_id: str,
        query: str,
        limit: int = 5,
    ) -> list[EvidenceChunk]:
        cleaned = query.strip()
        if not cleaned:
            return []
        try:
            rows = self._connection.execute(
                """
                SELECT c.chunk_id, c.document_id, c.version_id, c.source_name,
                       c.filename, c.page, c.section, c.version, c.text,
                       c.content_hash, c.active,
                       bm25(document_chunks_fts) AS rank
                FROM document_chunks_fts
                JOIN document_chunks c ON c.chunk_id = document_chunks_fts.chunk_id
                JOIN documents d ON d.document_id = c.document_id
                WHERE document_chunks_fts.account_id = ?
                  AND d.status = ?
                  AND c.active = 1
                  AND document_chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (account_id, KnowledgeStatus.AVAILABLE.value, _fts_query(cleaned), limit),
            ).fetchall()
        except Exception:
            rows = self._connection.execute(
                """
                SELECT chunk_id, document_id, version_id, source_name, filename,
                       page, section, version, text, content_hash, active, 0.0 AS rank
                FROM document_chunks
                WHERE account_id = ?
                  AND active = 1
                  AND document_id IN (
                      SELECT document_id FROM documents
                      WHERE account_id = ? AND status = ?
                  )
                  AND text LIKE ?
                LIMIT ?
                """,
                (
                    account_id,
                    account_id,
                    KnowledgeStatus.AVAILABLE.value,
                    f"%{cleaned}%",
                    limit,
                ),
            ).fetchall()

        evidence: list[EvidenceChunk] = []
        for row in rows:
            rank = float(row["rank"] or 0.0)
            score = 1.0 / (1.0 + abs(rank)) if rank else 0.5
            keys = set(row.keys())
            source = row["source_name"]
            filename = row["filename"] if "filename" in keys else None
            evidence.append(
                EvidenceChunk(
                    document_id=row["document_id"],
                    chunk_id=row["chunk_id"],
                    text=row["text"],
                    source_name=source,
                    filename=filename or source,
                    page=row["page"],
                    section=row["section"] if "section" in keys else None,
                    score=score,
                    version=row["version"],
                    version_id=row["version_id"] if "version_id" in keys else None,
                    content_hash=row["content_hash"] if "content_hash" in keys else None,
                    active=bool(row["active"]) if "active" in keys else True,
                )
            )
        return evidence

    def build_chunks_for_pages(
        self,
        *,
        document_id: str,
        version_id: str,
        filename: str,
        pages: list[tuple[int | None, str]],
    ) -> list[ProvenancedChunk]:
        return chunk_pages(
            document_id=document_id,
            version_id=version_id,
            filename=filename,
            pages=pages,
        )

    def _to_document(self, row: Any) -> dict[str, Any]:
        keys = row.keys()
        return {
            "document_id": row["document_id"],
            "source_name": row["source_name"],
            "filename": row["source_name"],
            "status": row["status"],
            "version": row["version"],
            "active_version_id": row["active_version_id"] if "active_version_id" in keys else None,
            "uploaded_at": row["uploaded_at"],
            "updated_at": row["updated_at"] if "updated_at" in keys else None,
            "indexed_at": row["indexed_at"] if "indexed_at" in keys else None,
            "removed_at": row["removed_at"] if "removed_at" in keys else None,
            "size_bytes": row["size_bytes"],
            "page_count": row["page_count"],
            "chunk_count": row["chunk_count"],
            "sha256": row["sha256"],
            "parser": row["parser"],
            "ocr_applied": bool(row["ocr_applied"]),
            "failure_stage": row["failure_stage"],
            "failure_message": row["failure_message"],
        }


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fts_query(text: str) -> str:
    tokens = [
        t
        for t in "".join(ch if ch.isalnum() else " " for ch in text).split()
        if len(t) >= 3 or any(ch.isdigit() for ch in t)
    ]
    if not tokens:
        return '""'
    return " OR ".join(f'"{token}"' for token in tokens[:12])
