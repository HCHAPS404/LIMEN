"""Shared FastAPI dependencies. Transport wiring only."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from limen.auth import Account, AuthService, SessionInvalid
from limen.config.settings import ApplicationSettings, get_settings
from limen.persistence.database import get_database
from limen.persistence.repositories import SqliteAccountRepository


def settings_dependency() -> ApplicationSettings:
    return get_settings()


Settings = Annotated[ApplicationSettings, Depends(settings_dependency)]


def auth_service_dependency(settings: Settings) -> AuthService:
    database = get_database(settings)
    return AuthService(
        SqliteAccountRepository(database),
        session_ttl=settings.auth_session_ttl(),
    )


Auth = Annotated[AuthService, Depends(auth_service_dependency)]


def session_token(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.auth_cookie_name)


def optional_account(
    auth: Auth,
    token: Annotated[str | None, Depends(session_token)],
) -> Account | None:
    """Resolves the caller when a valid session cookie is present.

    Used by surfaces that render for both visitors and signed-in clients.
    """
    if not token:
        return None
    try:
        return auth.authenticate(token)
    except SessionInvalid:
        return None


def require_account(
    auth: Auth,
    token: Annotated[str | None, Depends(session_token)],
) -> Account:
    """Guards every client-owned resource.

    Routes that read or write clinical documents, calls, or traces must depend on
    this and scope their queries to `account.account_id` (ADR-0004). `/health`
    stays public so operators can probe a cold deployment.
    """
    if not token:
        raise _unauthorized()
    try:
        return auth.authenticate(token)
    except SessionInvalid:
        raise _unauthorized() from None


CurrentAccount = Annotated[Account, Depends(require_account)]
OptionalAccount = Annotated[Account | None, Depends(optional_account)]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "session_invalid", "message": "Sign in to continue."},
    )
