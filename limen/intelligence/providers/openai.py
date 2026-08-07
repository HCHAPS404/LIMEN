"""OpenAI-compatible adapter placeholder.

Only enable when competition/runtime policy allows.
This module intentionally avoids importing a vendor SDK at foundation stage.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from limen.intelligence.contracts import LLMRequest, LLMResponse

T = TypeVar("T", bound=BaseModel)


class OpenAILLMProvider:
    """Reserved adapter — not wired for network calls in foundation."""

    def __init__(self, model: str, api_key: str = "", base_url: str = "") -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError(
            "OpenAI adapter is reserved. Set LLM_PROVIDER=stub or ollama for foundation."
        )

    async def generate_structured(self, request: LLMRequest, schema: type[T]) -> T:
        raise NotImplementedError(
            "OpenAI adapter is reserved. Set LLM_PROVIDER=stub or ollama for foundation."
        )
