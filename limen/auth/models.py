"""Auth domain objects. These are not API schemas and not ORM rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Account:
    """The identity every client-owned resource is scoped to."""

    account_id: str
    email: str
    display_name: str
    created_at: datetime


@dataclass(frozen=True)
class StoredAccount:
    """An account as persisted, including the password hash.

    Kept separate from `Account` so the hash cannot leak into a response by
    accident: transport layers only ever receive `Account`.
    """

    account_id: str
    email: str
    display_name: str
    created_at: datetime
    password_hash: str

    def public(self) -> Account:
        return Account(
            account_id=self.account_id,
            email=self.email,
            display_name=self.display_name,
            created_at=self.created_at,
        )


@dataclass(frozen=True)
class SessionRecord:
    """A session as persisted. Only the token hash is stored, never the token."""

    token_hash: str
    account_id: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class AuthenticatedSession:
    """Result of register/login. `token` exists only in this in-memory value."""

    token: str
    account: Account
    expires_at: datetime
