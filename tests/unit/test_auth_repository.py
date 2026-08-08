from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from limen.auth import AuthService, EmailAlreadyRegistered, SessionInvalid
from limen.persistence.database import Database
from limen.persistence.repositories import SqliteAccountRepository

PASSWORD = "umbral-seguro-2026"


@pytest.fixture
def service(tmp_path: Path) -> AuthService:
    database = Database(tmp_path / "accounts.db")
    database.initialize()
    return AuthService(
        SqliteAccountRepository(database),
        session_ttl=timedelta(hours=2),
    )


def test_account_survives_a_full_round_trip(service: AuthService) -> None:
    session = service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    account = service.authenticate(session.token)
    assert account.email == "clinica@umbral.io"
    assert account.display_name == "Clínica Umbral"
    assert account.created_at.tzinfo is not None


def test_unique_email_is_enforced_by_the_service_before_sqlite(
    service: AuthService,
) -> None:
    service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    with pytest.raises(EmailAlreadyRegistered):
        service.register("clinica@umbral.io", PASSWORD, "Otra")


def test_deleting_a_session_invalidates_the_token(service: AuthService) -> None:
    session = service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    service.logout(session.token)
    with pytest.raises(SessionInvalid):
        service.authenticate(session.token)


def test_expired_rows_are_purged(tmp_path: Path) -> None:
    database = Database(tmp_path / "accounts.db")
    database.initialize()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
    repository = SqliteAccountRepository(database)

    expired = AuthService(repository, session_ttl=timedelta(hours=-1), clock=lambda: now)
    expired.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")

    assert AuthService(repository, clock=lambda: now).purge_expired_sessions() == 1
    assert AuthService(repository, clock=lambda: now).purge_expired_sessions() == 0
