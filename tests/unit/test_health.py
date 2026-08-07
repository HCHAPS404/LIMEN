from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import create_app
from limen.config.settings import ApplicationSettings
from limen.persistence.database import reset_database_for_tests


def test_health_endpoint(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    reset_database_for_tests()
    # Clear settings cache
    from limen.config import settings as settings_mod

    settings_mod.get_settings.cache_clear()

    settings = ApplicationSettings(
        DATABASE_PATH=db_path,
        LLM_PROVIDER="stub",
        _env_file=None,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["llm_provider"] == "stub"
    assert payload["database"]["database"] == "ok"
    reset_database_for_tests()
    settings_mod.get_settings.cache_clear()
