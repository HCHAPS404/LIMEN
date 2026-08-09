"""UTC ISO helpers shared by SQLite repositories."""

from __future__ import annotations

from datetime import UTC, datetime


def to_text(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def from_text(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
