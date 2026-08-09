"""Deterministic stub LLM for local boot and tests."""

from __future__ import annotations

import json
import time
from typing import TypeVar

from pydantic import BaseModel

from limen.intelligence.contracts import LLMRequest, LLMResponse
from limen.intelligence.structured_output import parse_structured

T = TypeVar("T", bound=BaseModel)


class StubLLMProvider:
    """Echo-style LLM that never calls a network."""

    provider_name = "stub"

    def __init__(self, model: str = "stub-model") -> None:
        self.model = model

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        started = time.perf_counter()
        purpose = (request.metadata or {}).get("purpose", "")
        if purpose == "patient_response":
            # Deterministic safe phrasing for CI — never contradicts escalation
            # (RED path does not call the LLM).
            text = (
                "Gracias por contarme. Siga observando cómo se siente "
                "y avise si nota cambios importantes."
            )
        else:
            text = f"[stub:{self.model}] {request.prompt[:500]}"
        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.provider_name,
            prompt_tokens=len(request.prompt.split()),
            completion_tokens=len(text.split()),
            latency_ms=(time.perf_counter() - started) * 1000,
            generation_ms=(time.perf_counter() - started) * 1000,
            finish_reason="stop",
        )

    async def generate_structured(self, request: LLMRequest, schema: type[T]) -> T:
        # Minimal valid empty-ish JSON for schemas with defaults.
        payload = json.dumps({})
        try:
            return parse_structured(payload, schema)
        except ValueError:
            # Fall back to constructing with no args if possible.
            return schema()
