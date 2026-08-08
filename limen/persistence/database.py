"""SQLite persistence bootstrap."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from limen.config.settings import ApplicationSettings, get_settings

SCHEMA_VERSION = "2"

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
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    @property
    def connection(self) -> sqlite3.Connection:
        """Handed to repositories only; callers outside limen/persistence use a
        repository, never raw SQL."""
        return self._conn

    def initialize(self) -> None:
        self._conn.executescript(SCHEMA)
        self._conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("schema_version", SCHEMA_VERSION),
        )
        self._conn.commit()

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
