"""Helpers for structured LLM output validation."""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def extract_json_text(text: str) -> str:
    """Extract a JSON object/array from model text without inventing fields."""
    cleaned = text.strip()
    fence = _JSON_FENCE.search(cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    if cleaned.startswith("{") or cleaned.startswith("["):
        return cleaned
    # Find first JSON object/array span.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end > start:
            return cleaned[start : end + 1]
    return cleaned


def parse_structured(text: str, schema: type[T]) -> T:
    """Parse JSON text into a Pydantic schema. Does not silently repair fields."""
    payload = extract_json_text(text)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Structured output is not valid JSON: {exc}") from exc
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Structured output failed schema validation: {exc}") from exc
