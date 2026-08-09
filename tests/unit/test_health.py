from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import create_app
from limen.config.settings import ApplicationSettings
from limen.persistence.database import reset_database_for_tests


def test_health_endpoint(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("VECTOR_PATH", str(tmp_path / "vectors"))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    reset_database_for_tests()
    from limen.config import settings as settings_mod
    from limen.knowledge.vector_store import reset_vector_store_for_tests

    settings_mod.get_settings.cache_clear()
    reset_vector_store_for_tests()

    settings = ApplicationSettings(
        DATABASE_PATH=db_path,
        VECTOR_PATH=tmp_path / "vectors",
        EMBEDDING_PROVIDER="stub",
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
    assert payload["degraded_llm_mode"] is False
    assert payload["database"]["database"] == "ok"
    reset_vector_store_for_tests()
    reset_database_for_tests()
    settings_mod.get_settings.cache_clear()
