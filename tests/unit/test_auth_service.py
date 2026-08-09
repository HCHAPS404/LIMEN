from datetime import UTC, datetime, timedelta

import pytest

from limen.auth import (
    AuthService,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidEmail,
    SessionInvalid,
    WeakPassword,
)
from limen.auth.models import SessionRecord, StoredAccount

PASSWORD = "umbral-seguro-2026"


class InMemoryAccountRepository:
    """Exercises the contract without SQLite, so service rules stay isolated."""

    def __init__(self) -> None:
        self.accounts: dict[str, StoredAccount] = {}
        self.sessions: dict[str, SessionRecord] = {}

    def insert_account(self, account: StoredAccount) -> None:
        self.accounts[account.account_id] = account

    def find_account_by_email(self, email: str) -> StoredAccount | None:
        return next((a for a in self.accounts.values() if a.email == email), None)

    def find_account_by_id(self, account_id: str) -> StoredAccount | None:
        return self.accounts.get(account_id)

    def delete_account(self, account_id: str) -> None:
        self.accounts.pop(account_id, None)
        stale = [k for k, v in self.sessions.items() if v.account_id == account_id]
        for key in stale:
            del self.sessions[key]

    def insert_session(self, session: SessionRecord) -> None:
        self.sessions[session.token_hash] = session

    def find_session(self, token_hash: str) -> SessionRecord | None:
        return self.sessions.get(token_hash)

    def delete_session(self, token_hash: str) -> None:
        self.sessions.pop(token_hash, None)

    def delete_sessions_expired_before(self, moment: datetime) -> int:
        expired = [k for k, v in self.sessions.items() if v.expires_at <= moment]
        for key in expired:
            del self.sessions[key]
        return len(expired)


class MovableClock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


@pytest.fixture
def repository() -> InMemoryAccountRepository:
    return InMemoryAccountRepository()


@pytest.fixture
def service(repository: InMemoryAccountRepository) -> AuthService:
    return AuthService(repository, session_ttl=timedelta(hours=2))


def test_register_then_authenticate_returns_the_same_account(service: AuthService) -> None:
    session = service.register("Clinica@Umbral.io", PASSWORD, "Clínica Umbral")
    assert session.account.email == "clinica@umbral.io"

    account = service.authenticate(session.token)
    assert account.account_id == session.account.account_id
    assert account.display_name == "Clínica Umbral"


def test_login_accepts_a_registered_account(service: AuthService) -> None:
    service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    session = service.login("CLINICA@umbral.io", PASSWORD)
    assert service.authenticate(session.token).email == "clinica@umbral.io"


def test_login_with_wrong_password_is_rejected(service: AuthService) -> None:
    service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    with pytest.raises(InvalidCredentials):
        service.login("clinica@umbral.io", "otra-contrasena")


def test_login_for_unknown_email_reports_the_same_error(service: AuthService) -> None:
    # Identical error type and message: the form must not enumerate accounts.
    with pytest.raises(InvalidCredentials) as unknown:
        service.login("nadie@umbral.io", PASSWORD)
    service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    with pytest.raises(InvalidCredentials) as wrong_password:
        service.login("clinica@umbral.io", "otra-contrasena")
    assert str(unknown.value) == str(wrong_password.value)


def test_duplicate_email_is_refused_case_insensitively(service: AuthService) -> None:
    service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    with pytest.raises(EmailAlreadyRegistered):
        service.register("Clinica@Umbral.IO", PASSWORD, "Otra")


def test_invalid_email_and_short_password_are_refused(service: AuthService) -> None:
    with pytest.raises(InvalidEmail):
        service.register("sin-arroba", PASSWORD, "Clínica")
    with pytest.raises(WeakPassword):
        service.register("clinica@umbral.io", "corta", "Clínica")


def test_logout_revokes_the_session(service: AuthService) -> None:
    session = service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    service.logout(session.token)
    with pytest.raises(SessionInvalid):
        service.authenticate(session.token)


def test_logout_is_idempotent(service: AuthService) -> None:
    session = service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    service.logout(session.token)
    service.logout(session.token)
    service.logout("never-issued")


def test_expired_session_is_rejected_and_discarded(
    repository: InMemoryAccountRepository,
) -> None:
    clock = MovableClock(datetime(2026, 8, 7, 12, 0, tzinfo=UTC))
    service = AuthService(repository, session_ttl=timedelta(hours=1), clock=clock)
    session = service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")

    clock.advance(timedelta(hours=1, seconds=1))
    with pytest.raises(SessionInvalid):
        service.authenticate(session.token)
    assert repository.sessions == {}


def test_unknown_token_is_rejected(service: AuthService) -> None:
    with pytest.raises(SessionInvalid):
        service.authenticate("never-issued")


def test_stored_account_never_exposes_its_hash(service: AuthService) -> None:
    session = service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    assert not hasattr(session.account, "password_hash")


def test_session_token_is_not_stored_verbatim(
    service: AuthService, repository: InMemoryAccountRepository
) -> None:
    session = service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    assert session.token not in repository.sessions


def test_ensure_account_is_idempotent(service: AuthService) -> None:
    first = service.ensure_account("demo@limen.local", PASSWORD, "LIMEN Demo")
    second = service.ensure_account("demo@limen.local", "otra-contrasena-larga", "Otro")
    assert first.account_id == second.account_id
    # The seeded password is not rewritten from configuration on later runs.
    assert service.login("demo@limen.local", PASSWORD).account.account_id == first.account_id


def test_delete_account_removes_account_and_sessions(
    service: AuthService, repository: InMemoryAccountRepository
) -> None:
    session = service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    service.delete_account(session.account.account_id)
    assert repository.accounts == {}
    assert repository.sessions == {}
    with pytest.raises(SessionInvalid):
        service.authenticate(session.token)
    with pytest.raises(InvalidCredentials):
        service.login("clinica@umbral.io", PASSWORD)


def test_purge_expired_sessions_removes_only_stale_rows(
    repository: InMemoryAccountRepository,
) -> None:
    clock = MovableClock(datetime(2026, 8, 7, 12, 0, tzinfo=UTC))
    service = AuthService(repository, session_ttl=timedelta(hours=1), clock=clock)
    expiring = service.register("clinica@umbral.io", PASSWORD, "Clínica Umbral")
    clock.advance(timedelta(minutes=59))
    fresh = service.login("clinica@umbral.io", PASSWORD)

    clock.advance(timedelta(minutes=2))
    assert service.purge_expired_sessions() == 1
    with pytest.raises(SessionInvalid):
        service.authenticate(expiring.token)
    assert service.authenticate(fresh.token).email == "clinica@umbral.io"
