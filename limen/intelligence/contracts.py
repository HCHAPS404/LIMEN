"""LLM provider contracts — vendor SDKs must not leak past adapters."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class LLMRequest(BaseModel):
    """Provider-neutral generation request."""

    prompt: str
    system: str | None = None
    temperature: float = 0.2
    max_tokens: int | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    # When set, adapters MAY request constrained JSON matching this schema.
    response_json_schema: dict[str, Any] | None = None


class LLMResponse(BaseModel):
    """Provider-neutral generation response."""

    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float | None = None
    time_to_first_token_ms: float | None = None
    generation_ms: float | None = None
    finish_reason: str | None = None
    provider: str | None = None
    usage_metadata: dict[str, Any] = Field(default_factory=dict)


class LLMProvider(Protocol):
    async def generate_text(self, request: LLMRequest) -> LLMResponse: ...

    async def generate_structured(
        self,
        request: LLMRequest,
        schema: type[T],
    ) -> T: ...
