"""Anthropic adapter placeholder — reserved for allowed runtimes."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from limen.intelligence.contracts import LLMRequest, LLMResponse

T = TypeVar("T", bound=BaseModel)


class AnthropicLLMProvider:
    def __init__(self, model: str, api_key: str = "") -> None:
        self.model = model
        self.api_key = api_key

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError(
            "Anthropic adapter is reserved. Set LLM_PROVIDER=stub or ollama for foundation."
        )

    async def generate_structured(self, request: LLMRequest, schema: type[T]) -> T:
        raise NotImplementedError(
            "Anthropic adapter is reserved. Set LLM_PROVIDER=stub or ollama for foundation."
        )
