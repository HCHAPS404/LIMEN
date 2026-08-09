"""SQLite implementation of the auth storage contract."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from limen.auth.models import SessionRecord, StoredAccount
from limen.persistence.database import Database


def _to_text(moment: datetime) -> str:
    """Store UTC ISO-8601 so string ordering matches chronological ordering."""
    return moment.astimezone(UTC).isoformat()


def _from_text(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class SqliteAccountRepository:
    def __init__(self, database: Database) -> None:
        self._connection = database.connection

    def insert_account(self, account: StoredAccount) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO accounts
                    (account_id, email, display_name, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account.account_id,
                    account.email,
                    account.display_name,
                    account.password_hash,
                    _to_text(account.created_at),
                ),
            )

    def find_account_by_email(self, email: str) -> StoredAccount | None:
        return self._read_account("email", email)

    def find_account_by_id(self, account_id: str) -> StoredAccount | None:
        return self._read_account("account_id", account_id)

    def delete_account(self, account_id: str) -> None:
        """Removes the account; auth_sessions cascade via the FK."""
        with self._connection:
            self._connection.execute(
                "DELETE FROM accounts WHERE account_id = ?",
                (account_id,),
            )

    def insert_session(self, session: SessionRecord) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO auth_sessions
                    (token_hash, account_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    session.token_hash,
                    session.account_id,
                    _to_text(session.created_at),
                    _to_text(session.expires_at),
                ),
            )

    def find_session(self, token_hash: str) -> SessionRecord | None:
        row = self._connection.execute(
            """
            SELECT token_hash, account_id, created_at, expires_at
            FROM auth_sessions WHERE token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        return SessionRecord(
            token_hash=row["token_hash"],
            account_id=row["account_id"],
            created_at=_from_text(row["created_at"]),
            expires_at=_from_text(row["expires_at"]),
        )

    def delete_session(self, token_hash: str) -> None:
        with self._connection:
            self._connection.execute(
                "DELETE FROM auth_sessions WHERE token_hash = ?",
                (token_hash,),
            )

    def delete_sessions_expired_before(self, moment: datetime) -> int:
        with self._connection:
            cursor = self._connection.execute(
                "DELETE FROM auth_sessions WHERE expires_at <= ?",
                (_to_text(moment),),
            )
        return cursor.rowcount if cursor.rowcount > 0 else 0

    def _read_account(self, column: str, value: str) -> StoredAccount | None:
        # `column` is chosen from two literals above, never from request input.
        row: sqlite3.Row | None = self._connection.execute(
            f"""
            SELECT account_id, email, display_name, password_hash, created_at
            FROM accounts WHERE {column} = ?
            """,
            (value,),
        ).fetchone()
        if row is None:
            return None
        return StoredAccount(
            account_id=row["account_id"],
            email=row["email"],
            display_name=row["display_name"],
            created_at=_from_text(row["created_at"]),
            password_hash=row["password_hash"],
        )
