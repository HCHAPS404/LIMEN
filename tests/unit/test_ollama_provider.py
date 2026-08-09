"""Unit tests for Ollama adapter normalization (HTTP mocked)."""

from __future__ import annotations

import json

import httpx
import pytest

from limen.intelligence.contracts import LLMRequest
from limen.intelligence.providers.ollama import OllamaLLMProvider
from limen.intelligence.structured_output import parse_structured
from evals.llm.schemas import BenchmarkInterpretation


@pytest.mark.asyncio
async def test_ollama_generate_text_normalizes_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLLMProvider(model="llama3.2:1b")

    payload = {
        "model": "llama3.2:1b",
        "message": {"role": "assistant", "content": "hola"},
        "prompt_eval_count": 12,
        "eval_count": 3,
        "prompt_eval_duration": 50_000_000,
        "eval_duration": 80_000_000,
        "total_duration": 150_000_000,
        "done_reason": "stop",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        body = json.loads(request.content.decode())
        assert body["options"]["temperature"] == 0.2
        assert body["options"]["num_predict"] == 16
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    original = httpx.AsyncClient

    def client_factory(*args, **kwargs):  # noqa: ANN002, ANN003
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    response = await provider.generate_text(
        LLMRequest(prompt="di hola", temperature=0.2, max_tokens=16)
    )
    assert response.text == "hola"
    assert response.provider == "ollama"
    assert response.prompt_tokens == 12
    assert response.completion_tokens == 3
    assert response.time_to_first_token_ms == pytest.approx(50.0)
    assert response.generation_ms == pytest.approx(80.0)
    usage = provider.to_provider_usage(response)
    assert usage.input_tokens == 12
    assert usage.cost.cost_basis == "not_available"


@pytest.mark.asyncio
async def test_structured_tracked_counts_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLLMProvider(model="llama3.2:1b")
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            content = "not-json"
        else:
            content = json.dumps(
                {
                    "findings": [],
                    "negations": ["no fiebre"],
                    "symptom_descriptions": [],
                    "temporal_information": [],
                    "severity_qualifiers": [],
                    "uncertainties": [],
                    "contradictions": [],
                    "missing_information": [],
                }
            )
        return httpx.Response(
            200,
            json={
                "model": "llama3.2:1b",
                "message": {"content": content},
                "prompt_eval_count": 1,
                "eval_count": 1,
            },
        )

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def client_factory(*args, **kwargs):  # noqa: ANN002, ANN003
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    parsed, responses = await provider.generate_structured_tracked(
        LLMRequest(prompt="x"),
        BenchmarkInterpretation,
        max_attempts=2,
    )
    assert isinstance(parsed, BenchmarkInterpretation)
    assert len(responses) == 2
    assert parse_structured(responses[1].text, BenchmarkInterpretation)
