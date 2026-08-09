"""Structured logging helpers aligned with TRAZA identifiers."""

from __future__ import annotations

import logging
from typing import Any


def get_telemetry_logger(name: str = "limen.telemetry") -> logging.Logger:
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    event_type: str,
    *,
    call_id: str | None = None,
    turn_id: str | None = None,
    document_id: str | None = None,
    status: str = "ok",
    duration_ms: float | None = None,
    **extra: Any,
) -> None:
    """Emit a structured log line without patient text or secrets."""
    payload = {
        "event_type": event_type,
        "status": status,
        "call_id": call_id,
        "turn_id": turn_id,
        "document_id": document_id,
        "duration_ms": duration_ms,
    }
    for key, value in extra.items():
        if key in {"api_key", "password", "token", "secret"}:
            continue
        if key in {"text", "patient_text", "utterance", "prompt"}:
            continue
        payload[key] = value
    logger.info("traza %s", event_type, extra={"traza": payload})
