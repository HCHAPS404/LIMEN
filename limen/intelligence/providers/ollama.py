"""Ollama LLM adapter — HTTP only, no vendor SDK required."""

from __future__ import annotations

import time
from typing import TypeVar

import httpx
from pydantic import BaseModel

from limen.intelligence.contracts import LLMRequest, LLMResponse
from limen.intelligence.structured_output import parse_structured

T = TypeVar("T", bound=BaseModel)


class OllamaLLMProvider:
    """LLMProvider backed by Ollama's local HTTP API."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_s: float = 60.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        started = time.perf_counter()
        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            data = response.json()

        text = str(data.get("message", {}).get("content", ""))
        return LLMResponse(
            text=text,
            model=self.model,
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
            completion_tokens=int(data.get("eval_count") or 0),
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    async def generate_structured(self, request: LLMRequest, schema: type[T]) -> T:
        schema_hint = (
            f"{request.prompt}\n\nRespond with JSON matching this schema:\n"
            f"{schema.model_json_schema()}"
        )
        structured_request = request.model_copy(update={"prompt": schema_hint})
        response = await self.generate_text(structured_request)
        return parse_structured(response.text, schema)
