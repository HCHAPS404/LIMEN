"""ORM-ish persistence models — never expose as public API schemas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SessionRow:
    session_id: str
    created_at: str
    payload_json: str
