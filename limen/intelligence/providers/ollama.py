"""Ollama LLM adapter — HTTP only, no vendor SDK required."""

from __future__ import annotations

import json
import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from limen.intelligence.contracts import LLMRequest, LLMResponse
from limen.intelligence.structured_output import parse_structured
from limen.telemetry.cost import cost_not_available
from limen.tracing.contracts import ProviderUsage

T = TypeVar("T", bound=BaseModel)

# G3-allowed local families for PHASE 5 (exact tags used with Ollama).
G3_ALLOWED_OLLAMA_MODELS: frozenset[str] = frozenset(
    {
        "llama3.2:1b",
        "llama3.2:3b",
        "phi3.5",
        "phi3.5:latest",
        "phi3.5:3.8b",
    }
)


def is_g3_allowed_ollama_model(model: str) -> bool:
    name = model.strip().lower()
    if name in G3_ALLOWED_OLLAMA_MODELS:
        return True
    # Accept digest-qualified tags that start with an allowed id.
    return any(
        name.startswith(f"{allowed}@") or name.startswith(f"{allowed}:")
        for allowed in (
            "llama3.2:1b",
            "llama3.2:3b",
            "phi3.5",
        )
    )


class OllamaLLMProvider:
    """LLMProvider backed by Ollama's local HTTP API."""

    provider_name = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_s: float = 180.0,
        *,
        default_temperature: float = 0.2,
        default_max_tokens: int | None = 256,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=min(self.timeout_s, 10.0)) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
        models = [str(item.get("name", "")) for item in data.get("models", [])]
        return {
            "ok": True,
            "base_url": self.base_url,
            "models": models,
            "selected_model": self.model,
            "selected_available": any(
                m == self.model or m.startswith(f"{self.model}:") or m.startswith(self.model)
                for m in models
            ),
        }

    async def show_model(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(
                f"{self.base_url}/api/show",
                json={"name": self.model},
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                return {"raw": data}
            return data

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        started = time.perf_counter()
        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        temperature = (
            request.temperature if request.temperature is not None else self.default_temperature
        )
        max_tokens = (
            request.max_tokens if request.max_tokens is not None else self.default_max_tokens
        )
        options: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        if request.response_json_schema is not None:
            # Ollama constrained decoding — return a JSON *instance*, not the schema text.
            payload["format"] = request.response_json_schema

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")
        # Ollama reports nanosecond totals when present.
        prompt_ns = data.get("prompt_eval_duration")
        eval_ns = data.get("eval_duration")
        total_ns = data.get("total_duration")
        generation_ms = (float(eval_ns) / 1e6) if eval_ns is not None else None
        # TTFT approximation: time before token generation (prompt eval).
        ttft_ms = (float(prompt_ns) / 1e6) if prompt_ns is not None else None
        if generation_ms is None and total_ns is not None and prompt_ns is not None:
            generation_ms = (float(total_ns) - float(prompt_ns)) / 1e6

        return LLMResponse(
            text=str(data.get("message", {}).get("content", "")),
            model=str(data.get("model") or self.model),
            provider=self.provider_name,
            prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
            completion_tokens=int(completion_tokens) if completion_tokens is not None else None,
            latency_ms=elapsed_ms,
            time_to_first_token_ms=ttft_ms,
            generation_ms=generation_ms,
            finish_reason=str(data.get("done_reason")) if data.get("done_reason") else None,
            usage_metadata={
                "total_duration_ns": total_ns,
                "load_duration_ns": data.get("load_duration"),
                "prompt_eval_duration_ns": prompt_ns,
                "eval_duration_ns": eval_ns,
            },
        )

    async def generate_structured(self, request: LLMRequest, schema: type[T]) -> T:
        parsed, _responses = await self.generate_structured_tracked(request, schema, max_attempts=1)
        return parsed

    async def generate_structured_tracked(
        self,
        request: LLMRequest,
        schema: type[T],
        *,
        max_attempts: int = 1,
    ) -> tuple[T, list[LLMResponse]]:
        """Return (parsed, raw_responses). Retries count as extra invocations.

        Malformed output is not silently repaired into success.
        """
        # Ask for an instance, not a restatement of the JSON Schema document.
        schema_json = schema.model_json_schema()
        example = {
            name: ("GREEN" if name == "proposed_risk" else ([] if name == "reasons" else "low"))
            for name in schema_json.get("properties", {})
        }
        # Prefer concrete example keys from the pydantic model fields when available.
        if "proposed_risk" in schema.model_fields:
            example = {"proposed_risk": "GREEN", "reasons": ["breve"], "confidence": "low"}
        schema_hint = (
            f"{request.prompt}\n\n"
            "Return ONLY one JSON object instance (not the schema definition).\n"
            f"Example shape: {json.dumps(example, ensure_ascii=False)}\n"
            "No markdown fences. No extra keys beyond the schema."
        )
        structured_request = request.model_copy(
            update={
                "prompt": schema_hint,
                "response_json_schema": schema_json,
            }
        )
        responses: list[LLMResponse] = []
        last_error: Exception | None = None
        for _ in range(max(1, max_attempts)):
            response = await self.generate_text(structured_request)
            responses.append(response)
            try:
                return parse_structured(response.text, schema), responses
            except ValueError as exc:
                last_error = exc
        assert last_error is not None
        raise ValueError(str(last_error)) from last_error

    def to_provider_usage(self, response: LLMResponse) -> ProviderUsage:
        return ProviderUsage(
            provider=self.provider_name,
            model=response.model,
            input_tokens=response.prompt_tokens,
            output_tokens=response.completion_tokens,
            latency_ms=response.latency_ms,
            generation_ms=response.generation_ms,
            time_to_first_token_ms=response.time_to_first_token_ms,
            finish_reason=response.finish_reason,
            llm_calls=1,
            cost=cost_not_available(notes="local_ollama_no_api_fee_pricing_unconfigured"),
        )
