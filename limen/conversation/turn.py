"""Conversation turn model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class Turn(BaseModel):
    turn_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    user_text: str
    assistant_text: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
