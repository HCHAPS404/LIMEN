"""Optional real Ollama integration for PHASE 5 (skipped unless enabled)."""

from __future__ import annotations

import os

import httpx
import pytest

from limen.intelligence.contracts import LLMRequest
from limen.intelligence.providers.ollama import OllamaLLMProvider, is_g3_allowed_ollama_model

pytestmark = pytest.mark.real_llm

_REAL = os.environ.get("LIMEN_REAL_LLM", "").strip() in {"1", "true", "yes"}
_BASE = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def _ollama_up() -> bool:
    try:
        response = httpx.get(f"{_BASE}/api/tags", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.mark.asyncio
async def test_ollama_health_and_one_completion_when_available() -> None:
    if not _REAL:
        pytest.skip("Set LIMEN_REAL_LLM=1 to run real Ollama tests")
    if not _ollama_up():
        pytest.skip(f"Ollama not reachable at {_BASE}")

    provider = OllamaLLMProvider(model="llama3.2:1b", base_url=_BASE, timeout_s=120.0)
    health = await provider.health()
    assert health["ok"] is True
    models = health["models"]
    tag = None
    for candidate in ("llama3.2:1b", "llama3.2:3b", "phi3.5", "phi3.5:latest"):
        for installed in models:
            if installed == candidate or installed.startswith(f"{candidate}:"):
                tag = installed
                break
        if tag:
            break
    if tag is None:
        pytest.skip(f"No G3-allowed model installed; available={models}")

    assert is_g3_allowed_ollama_model(tag)
    provider = OllamaLLMProvider(model=tag, base_url=_BASE, timeout_s=180.0)
    response = await provider.generate_text(
        LLMRequest(prompt="Di solo: hola", system="Responde breve en español.", max_tokens=16)
    )
    assert response.text
    assert response.provider == "ollama"
    usage = provider.to_provider_usage(response)
    assert usage.provider == "ollama"
    assert usage.model
    # Tokens may be present from Ollama; do not fabricate if missing.
    assert usage.latency_ms is None or usage.latency_ms >= 0


@pytest.mark.asyncio
async def test_one_request_per_available_g3_candidate() -> None:
    """PHASE 5B: one real request per installed allowed candidate + identity/telemetry."""
    if not _REAL:
        pytest.skip("Set LIMEN_REAL_LLM=1 to run real Ollama tests")
    if not _ollama_up():
        pytest.skip(f"Ollama not reachable at {_BASE}")

    probe = OllamaLLMProvider(model="llama3.2:1b", base_url=_BASE, timeout_s=30.0)
    health = await probe.health()
    models = [m.lower() for m in health["models"]]
    aliases = {
        "llama3.2:1b": ("llama3.2:1b",),
        "llama3.2:3b": ("llama3.2:3b",),
        "phi3.5": ("phi3.5", "phi3.5:latest", "phi3.5:3.8b"),
    }
    ran = 0
    for _candidate_id, tags in aliases.items():
        resolved = None
        for tag in tags:
            for installed in health["models"]:
                lowered = installed.lower()
                tag_l = tag.lower()
                if lowered == tag_l or lowered.startswith(f"{tag_l}@"):
                    resolved = installed
                    break
            if resolved:
                break
        if resolved is None:
            continue
        assert is_g3_allowed_ollama_model(resolved)
        provider = OllamaLLMProvider(model=resolved, base_url=_BASE, timeout_s=180.0)
        shown = await provider.show_model()
        assert isinstance(shown, dict)
        response = await provider.generate_text(
            LLMRequest(prompt="Di solo: ok", system="breve", max_tokens=8)
        )
        assert response.provider == "ollama"
        assert response.model
        usage = provider.to_provider_usage(response)
        assert usage.provider == "ollama"
        assert usage.model
        # Do not fabricate tokens.
        assert usage.input_tokens is None or usage.input_tokens >= 0
        assert usage.output_tokens is None or usage.output_tokens >= 0
        ran += 1
    if ran == 0:
        pytest.skip(f"No G3 candidates installed; available={models}")
