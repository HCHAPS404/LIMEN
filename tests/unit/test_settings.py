from limen.config.settings import ApplicationSettings


def test_settings_defaults(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    settings = ApplicationSettings(_env_file=None)
    assert settings.llm_provider == "stub"
    assert settings.app_port == 8000
    origins = settings.cors_origin_list()
    assert len(origins) >= 1
    assert any("5173" in origin for origin in origins)
