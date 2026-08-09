"""Build LLM providers from application settings."""

from __future__ import annotations

import threading

from limen.config.settings import ApplicationSettings
from limen.intelligence.contracts import LLMProvider
from limen.intelligence.providers.ollama import OllamaLLMProvider
from limen.intelligence.providers.stub import StubLLMProvider

_cache_lock = threading.Lock()
_cached_provider: LLMProvider | None = None
_cached_key: str | None = None


def _llm_cache_key(settings: ApplicationSettings) -> str:
    return "|".join(
        [
            settings.llm_provider.lower().strip(),
            settings.llm_model or "",
            settings.llm_base_url or "",
            str(settings.llm_timeout_s),
            str(settings.llm_temperature),
            str(settings.llm_max_tokens),
        ]
    )


def reset_llm_provider_for_tests() -> None:
    """Drop process-wide LLM singleton (tests only)."""
    global _cached_provider, _cached_key
    with _cache_lock:
        _cached_provider = None
        _cached_key = None


def build_llm_provider(settings: ApplicationSettings) -> LLMProvider:
    """Return a process-wide singleton per LLM configuration."""
    global _cached_provider, _cached_key
    key = _llm_cache_key(settings)
    with _cache_lock:
        if _cached_provider is not None and _cached_key == key:
            return _cached_provider

        provider = settings.llm_provider.lower().strip()
        if provider == "stub":
            built: LLMProvider = StubLLMProvider(model=settings.llm_model)
        elif provider == "ollama":
            base = settings.llm_base_url or "http://127.0.0.1:11434"
            built = OllamaLLMProvider(
                model=settings.llm_model,
                base_url=base,
                timeout_s=float(settings.llm_timeout_s),
                default_temperature=settings.llm_temperature,
                default_max_tokens=settings.llm_max_tokens,
            )
        else:
            raise ValueError(
                f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. "
                "Use 'stub' or 'ollama' in foundation."
            )
        _cached_provider = built
        _cached_key = key
        return built
