"""Build LLM providers from application settings."""

from __future__ import annotations

from limen.config.settings import ApplicationSettings
from limen.intelligence.contracts import LLMProvider
from limen.intelligence.providers.ollama import OllamaLLMProvider
from limen.intelligence.providers.stub import StubLLMProvider


def build_llm_provider(settings: ApplicationSettings) -> LLMProvider:
    provider = settings.llm_provider.lower().strip()
    if provider == "stub":
        return StubLLMProvider(model=settings.llm_model)
    if provider == "ollama":
        base = settings.llm_base_url or "http://127.0.0.1:11434"
        return OllamaLLMProvider(model=settings.llm_model, base_url=base)
    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. Use 'stub' or 'ollama' in foundation."
    )
