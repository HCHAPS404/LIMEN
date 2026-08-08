"""Auth endpoints over the real SQLite schema and the real cookie plumbing."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from limen.config import settings as settings_module
from limen.persistence.database import reset_database_for_tests

PASSWORD = "umbral-seguro-2026"
COOKIE = "limen_session"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # Request handling resolves settings and the database through module-level
    # caches, so the temporary path has to be visible before the first call.
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "auth.db"))
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    settings_module.get_settings.cache_clear()
    reset_database_for_tests()

    settings = settings_module.get_settings()
    assert settings.database_path == tmp_path / "auth.db"

    with TestClient(create_app(settings)) as test_client:
        yield test_client

    reset_database_for_tests()
    settings_module.get_settings.cache_clear()


def register(client: TestClient, email: str = "clinica@umbral.io") -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Clínica Umbral"},
    )
    assert response.status_code == 201, response.text


def test_register_login_me_logout_round_trip(client: TestClient) -> None:
    created = client.post(
        "/api/auth/register",
        json={
            "email": "Clinica@Umbral.io",
            "password": PASSWORD,
            "display_name": "Clínica Umbral",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["account"]["email"] == "clinica@umbral.io"
    assert body["account"]["display_name"] == "Clínica Umbral"
    assert "password" not in created.text and "hash" not in created.text
    assert COOKIE in created.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "clinica@umbral.io"

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    signed_in = client.post(
        "/api/auth/login",
        json={"email": "clinica@umbral.io", "password": PASSWORD},
    )
    assert signed_in.status_code == 200
    assert client.get("/api/auth/me").json()["email"] == "clinica@umbral.io"


def test_session_cookie_is_http_only(client: TestClient) -> None:
    created = client.post(
        "/api/auth/register",
        json={"email": "clinica@umbral.io", "password": PASSWORD, "display_name": "C"},
    )
    cookie_header = created.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header


def test_wrong_password_is_unauthorized(client: TestClient) -> None:
    register(client)
    client.post("/api/auth/logout")
    response = client.post(
        "/api/auth/login",
        json={"email": "clinica@umbral.io", "password": "otra-contrasena"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_unknown_email_returns_the_same_code(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "nadie@umbral.io", "password": PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_duplicate_email_conflicts(client: TestClient) -> None:
    register(client)
    response = client.post(
        "/api/auth/register",
        json={"email": "CLINICA@umbral.io", "password": PASSWORD, "display_name": "Otra"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_taken"


def test_short_password_and_invalid_email_are_reported_separately(
    client: TestClient,
) -> None:
    weak = client.post(
        "/api/auth/register",
        json={"email": "clinica@umbral.io", "password": "corta", "display_name": "C"},
    )
    assert weak.status_code == 422
    assert weak.json()["detail"]["code"] == "weak_password"

    malformed = client.post(
        "/api/auth/register",
        json={"email": "sin-arroba", "password": PASSWORD, "display_name": "C"},
    )
    assert malformed.status_code == 422
    assert malformed.json()["detail"]["code"] == "invalid_email"


def test_me_requires_a_session(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "session_invalid"


def test_forged_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set(COOKIE, "forged-token")
    assert client.get("/api/auth/me").status_code == 401


def test_logout_without_a_session_still_succeeds(client: TestClient) -> None:
    assert client.post("/api/auth/logout").status_code == 204


def test_health_stays_public(client: TestClient) -> None:
    # Operators must be able to probe a deployment before any account exists.
    assert client.get("/health").status_code == 200
