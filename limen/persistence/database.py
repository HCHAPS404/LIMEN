"""SQLite persistence bootstrap."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from limen.config.settings import ApplicationSettings, get_settings

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
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def initialize(self) -> None:
        self._conn.executescript(SCHEMA)
        self._conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("schema_version", "1"),
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
