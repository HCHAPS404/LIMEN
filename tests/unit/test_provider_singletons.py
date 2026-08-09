"""Process-wide provider singletons must not reload heavy models per request."""

from __future__ import annotations

from limen.config.settings import ApplicationSettings
from limen.intelligence.providers.factory import (
    build_llm_provider,
    reset_llm_provider_for_tests,
)
from limen.knowledge.embeddings import (
    build_embedding_provider,
    reset_embedding_provider_for_tests,
)
from limen.voice.stt import build_stt_provider, reset_stt_provider_for_tests
from limen.voice.tts import build_tts_provider, reset_tts_provider_for_tests


def test_embedding_provider_is_singleton() -> None:
    reset_embedding_provider_for_tests()
    settings = ApplicationSettings(
        embedding_provider="stub",
        embedding_dimensions=32,
        _env_file=None,
    )
    a = build_embedding_provider(settings)
    b = build_embedding_provider(settings)
    assert a is b
    reset_embedding_provider_for_tests()


def test_stt_tts_llm_providers_are_singletons() -> None:
    reset_stt_provider_for_tests()
    reset_tts_provider_for_tests()
    reset_llm_provider_for_tests()
    settings = ApplicationSettings(
        stt_provider="stub",
        tts_provider="stub",
        llm_provider="stub",
        llm_model="stub-llm",
        _env_file=None,
    )
    assert build_stt_provider(settings) is build_stt_provider(settings)
    assert build_tts_provider(settings) is build_tts_provider(settings)
    assert build_llm_provider(settings) is build_llm_provider(settings)
    reset_stt_provider_for_tests()
    reset_tts_provider_for_tests()
    reset_llm_provider_for_tests()
