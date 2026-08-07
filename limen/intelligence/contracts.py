"""LLM provider contracts — vendor SDKs must not leak past adapters."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class LLMRequest(BaseModel):
    """Provider-neutral generation request."""

    prompt: str
    system: str | None = None
    temperature: float = 0.2
    max_tokens: int | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Provider-neutral generation response."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0


class LLMProvider(Protocol):
    async def generate_text(self, request: LLMRequest) -> LLMResponse: ...

    async def generate_structured(
        self,
        request: LLMRequest,
        schema: type[T],
    ) -> T: ...
