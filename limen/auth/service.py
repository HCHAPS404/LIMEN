"""Account registration, login, and session verification."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from limen.auth.contracts import AccountRepository
from limen.auth.errors import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidEmail,
    SessionInvalid,
    WeakPassword,
)
from limen.auth.models import (
    Account,
    AuthenticatedSession,
    SessionRecord,
    StoredAccount,
)
from limen.auth.passwords import (
    MINIMUM_PASSWORD_LENGTH,
    hash_password,
    verify_password,
)
from limen.auth.tokens import hash_token, new_session_token

DEFAULT_SESSION_TTL = timedelta(days=7)
MAX_DISPLAY_NAME_LENGTH = 80

# Deliberately permissive: rejecting valid institutional addresses is worse than
# accepting one that never receives mail. Delivery is not part of this flow.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(
        self,
        repository: AccountRepository,
        *,
        session_ttl: timedelta = DEFAULT_SESSION_TTL,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._repository = repository
        self._session_ttl = session_ttl
        self._clock = clock

    def register(self, email: str, password: str, display_name: str) -> AuthenticatedSession:
        normalized = normalize_email(email)
        if not _EMAIL_PATTERN.match(normalized):
            raise InvalidEmail(email)
        if len(password) < MINIMUM_PASSWORD_LENGTH:
            raise WeakPassword(MINIMUM_PASSWORD_LENGTH)
        if self._repository.find_account_by_email(normalized) is not None:
            raise EmailAlreadyRegistered(normalized)

        account = StoredAccount(
            account_id=uuid.uuid4().hex,
            email=normalized,
            display_name=(display_name.strip() or normalized)[:MAX_DISPLAY_NAME_LENGTH],
            created_at=self._clock(),
            password_hash=hash_password(password),
        )
        self._repository.insert_account(account)
        return self._open_session(account.public())

    def login(self, email: str, password: str) -> AuthenticatedSession:
        stored = self._repository.find_account_by_email(normalize_email(email))
        if stored is None or not verify_password(password, stored.password_hash):
            raise InvalidCredentials()
        return self._open_session(stored.public())

    def logout(self, token: str) -> None:
        """Idempotent: revoking an unknown or already-revoked token is a no-op."""
        self._repository.delete_session(hash_token(token))

    def authenticate(self, token: str) -> Account:
        session = self._repository.find_session(hash_token(token))
        if session is None:
            raise SessionInvalid()

        now = self._clock()
        if session.expires_at <= now:
            self._repository.delete_session(session.token_hash)
            raise SessionInvalid()

        stored = self._repository.find_account_by_id(session.account_id)
        if stored is None:
            # Account removed while the cookie was still alive.
            self._repository.delete_session(session.token_hash)
            raise SessionInvalid()
        return stored.public()

    def purge_expired_sessions(self) -> int:
        return self._repository.delete_sessions_expired_before(self._clock())

    def ensure_account(self, email: str, password: str, display_name: str) -> Account:
        """Idempotent seed used by bootstrap so a cold start has a demo login.

        An existing account is returned untouched; the stored password is never
        reset from configuration.
        """
        normalized = normalize_email(email)
        existing = self._repository.find_account_by_email(normalized)
        if existing is not None:
            return existing.public()
        return self.register(normalized, password, display_name).account

    def _open_session(self, account: Account) -> AuthenticatedSession:
        token = new_session_token()
        issued_at = self._clock()
        expires_at = issued_at + self._session_ttl
        self._repository.insert_session(
            SessionRecord(
                token_hash=hash_token(token),
                account_id=account.account_id,
                created_at=issued_at,
                expires_at=expires_at,
            )
        )
        return AuthenticatedSession(token=token, account=account, expires_at=expires_at)
