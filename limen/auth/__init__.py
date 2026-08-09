"""Account and session domain.

LIMEN is used by more than one clinic, and every clinic uploads its own clinical
corpus. Authentication exists to keep those corpora apart, not to add enterprise
identity features. See docs/adr/ADR-0004-client-auth.md.
"""

from limen.auth.contracts import AccountRepository
from limen.auth.errors import (
    AuthError,
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
from limen.auth.passwords import hash_password, verify_password
from limen.auth.service import AuthService
from limen.auth.tokens import hash_token, new_session_token

__all__ = [
    "Account",
    "AccountRepository",
    "AuthError",
    "AuthService",
    "AuthenticatedSession",
    "EmailAlreadyRegistered",
    "InvalidCredentials",
    "InvalidEmail",
    "SessionInvalid",
    "SessionRecord",
    "StoredAccount",
    "WeakPassword",
    "hash_password",
    "hash_token",
    "new_session_token",
    "verify_password",
]
