"""SQLite persistence bootstrap."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from limen.config.settings import ApplicationSettings, get_settings

SCHEMA_VERSION = "5"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

-- Client accounts. Every client-owned resource is scoped to account_id so two
-- clinics never share a clinical corpus (ADR-0004).
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Only the token digest is stored, so a database dump cannot be replayed.
CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_account ON auth_sessions(account_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expiry ON auth_sessions(expires_at);

CREATE TABLE IF NOT EXISTS calls (
    call_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    patient_alias TEXT NOT NULL,
    procedure TEXT,
    postoperative_day INTEGER,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_seconds INTEGER,
    final_risk TEXT,
    escalated INTEGER NOT NULL DEFAULT 0,
    clinical_state_json TEXT NOT NULL DEFAULT '{}',
    summary_json TEXT,
    metrics_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_calls_account ON calls(account_id);
CREATE INDEX IF NOT EXISTS idx_calls_started ON calls(started_at);

CREATE TABLE IF NOT EXISTS call_turns (
    turn_id TEXT PRIMARY KEY,
    call_id TEXT NOT NULL REFERENCES calls(call_id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    speaker TEXT NOT NULL,
    text TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    interrupted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_call_turns_call ON call_turns(call_id, sequence);

CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    status TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    active_version_id TEXT,
    uploaded_at TEXT NOT NULL,
    updated_at TEXT,
    indexed_at TEXT,
    removed_at TEXT,
    size_bytes INTEGER,
    page_count INTEGER,
    chunk_count INTEGER,
    sha256 TEXT,
    parser TEXT,
    ocr_applied INTEGER NOT NULL DEFAULT 0,
    failure_stage TEXT,
    failure_message TEXT,
    storage_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_account ON documents(account_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(account_id, status);
CREATE INDEX IF NOT EXISTS idx_documents_sha ON documents(account_id, sha256);

CREATE TABLE IF NOT EXISTS document_versions (
    version_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    content_hash TEXT NOT NULL,
    page_count INTEGER,
    chunk_count INTEGER,
    status TEXT NOT NULL,
    indexed_at TEXT,
    removed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_versions_document ON document_versions(document_id);

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    version_id TEXT,
    source_name TEXT NOT NULL,
    filename TEXT,
    page INTEGER,
    section TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    text TEXT NOT NULL,
    content_hash TEXT,
    ordinal INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_account ON document_chunks(account_id);

-- Standalone FTS index; repository keeps it in sync on ingest/delete.
CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(
    chunk_id UNINDEXED,
    account_id UNINDEXED,
    document_id UNINDEXED,
    source_name,
    text
);

CREATE TABLE IF NOT EXISTS knowledge_events (
    event_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    document_id TEXT,
    sequence INTEGER NOT NULL,
    stage TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    label TEXT NOT NULL,
    detail TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    event_type TEXT,
    duration_ms REAL,
    status TEXT,
    schema_version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_knowledge_events_doc
    ON knowledge_events(account_id, document_id, sequence);

CREATE TABLE IF NOT EXISTS trace_events (
    event_id TEXT PRIMARY KEY,
    call_id TEXT NOT NULL REFERENCES calls(call_id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    stage TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    label TEXT NOT NULL,
    detail TEXT,
    risk TEXT,
    escalate INTEGER,
    reasons_json TEXT NOT NULL DEFAULT '[]',
    evidence_json TEXT NOT NULL DEFAULT '[]',
    metrics_json TEXT,
    event_type TEXT,
    turn_id TEXT,
    document_id TEXT,
    duration_ms REAL,
    status TEXT,
    schema_version INTEGER NOT NULL DEFAULT 1,
    payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_trace_call ON trace_events(call_id, sequence);
"""

# Columns added after schema v3 for existing local databases.
_DOCUMENT_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("active_version_id", "TEXT"),
    ("updated_at", "TEXT"),
    ("indexed_at", "TEXT"),
    ("removed_at", "TEXT"),
)

_CHUNK_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("version_id", "TEXT"),
    ("filename", "TEXT"),
    ("section", "TEXT"),
    ("content_hash", "TEXT"),
    ("active", "INTEGER NOT NULL DEFAULT 1"),
)

_TRACE_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("event_type", "TEXT"),
    ("turn_id", "TEXT"),
    ("document_id", "TEXT"),
    ("duration_ms", "REAL"),
    ("status", "TEXT"),
    ("schema_version", "INTEGER NOT NULL DEFAULT 1"),
    ("payload_json", "TEXT NOT NULL DEFAULT '{}'"),
)

_KNOWLEDGE_EVENT_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("event_type", "TEXT"),
    ("duration_ms", "REAL"),
    ("status", "TEXT"),
    ("schema_version", "INTEGER NOT NULL DEFAULT 1"),
)


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")

    @property
    def connection(self) -> sqlite3.Connection:
        """Handed to repositories only; callers outside limen/persistence use a
        repository, never raw SQL."""
        return self._conn

    def initialize(self) -> None:
        self._conn.executescript(SCHEMA)
        self._apply_column_migrations()
        # Index that requires the `active` column — create after migrations.
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_active "
            "ON document_chunks(account_id, active)"
        )
        self._conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("schema_version", SCHEMA_VERSION),
        )
        self._conn.commit()

    def _apply_column_migrations(self) -> None:
        """Additive migrations for databases created before schema v5."""
        existing_docs = {
            row[1] for row in self._conn.execute("PRAGMA table_info(documents)").fetchall()
        }
        for name, decl in _DOCUMENT_COLUMN_MIGRATIONS:
            if name not in existing_docs:
                self._conn.execute(f"ALTER TABLE documents ADD COLUMN {name} {decl}")

        existing_chunks = {
            row[1] for row in self._conn.execute("PRAGMA table_info(document_chunks)").fetchall()
        }
        for name, decl in _CHUNK_COLUMN_MIGRATIONS:
            if name not in existing_chunks:
                self._conn.execute(f"ALTER TABLE document_chunks ADD COLUMN {name} {decl}")

        existing_traces = {
            row[1] for row in self._conn.execute("PRAGMA table_info(trace_events)").fetchall()
        }
        for name, decl in _TRACE_COLUMN_MIGRATIONS:
            if name not in existing_traces:
                self._conn.execute(f"ALTER TABLE trace_events ADD COLUMN {name} {decl}")

        existing_ke = {
            row[1] for row in self._conn.execute("PRAGMA table_info(knowledge_events)").fetchall()
        }
        for name, decl in _KNOWLEDGE_EVENT_COLUMN_MIGRATIONS:
            if name not in existing_ke:
                self._conn.execute(f"ALTER TABLE knowledge_events ADD COLUMN {name} {decl}")

    def health(self) -> dict[str, str]:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key = ?",
            ("schema_version",),
        ).fetchone()
        version = row["value"] if row else "missing"
        return {"database": "ok", "schema_version": version, "path": str(self.path)}

    def close(self) -> None:
        self._conn.close()


_db: Database | None = None


def get_database(settings: ApplicationSettings | None = None) -> Database:
    global _db
    if _db is None:
        cfg = settings or get_settings()
        _db = Database(cfg.database_path)
        _db.initialize()
    return _db


def reset_database_for_tests() -> None:
    global _db
    if _db is not None:
        _db.close()
    _db = None
