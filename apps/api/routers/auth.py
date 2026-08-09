"""Account endpoints.

Domain errors are translated to status codes plus a stable machine-readable
`code`, so the browser can localise the message instead of echoing English text.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from apps.api.dependencies import Auth, CurrentAccount, Settings, session_token
from apps.api.schemas.auth import (
    AccountResponse,
    LoginRequest,
    RegisterRequest,
    SessionResponse,
)
from limen.auth import (
    AuthenticatedSession,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidEmail,
    WeakPassword,
)
from limen.config.settings import ApplicationSettings

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Starlette renamed the 422 constant; the numeric code is the stable contract.
UNPROCESSABLE = 422


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _set_session_cookie(
    response: Response,
    settings: ApplicationSettings,
    session: AuthenticatedSession,
) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=session.token,
        max_age=int(settings.auth_session_ttl().total_seconds()),
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    response: Response,
    auth: Auth,
    settings: Settings,
) -> SessionResponse:
    try:
        session = auth.register(payload.email, payload.password, payload.display_name)
    except InvalidEmail as error:
        raise _error(UNPROCESSABLE, "invalid_email", str(error)) from error
    except WeakPassword as error:
        raise _error(UNPROCESSABLE, "weak_password", str(error)) from error
    except EmailAlreadyRegistered as error:
        raise _error(status.HTTP_409_CONFLICT, "email_taken", str(error)) from error

    _set_session_cookie(response, settings, session)
    return SessionResponse(
        account=AccountResponse.from_account(session.account),
        expires_at=session.expires_at,
    )


@router.post("/login", response_model=SessionResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    auth: Auth,
    settings: Settings,
) -> SessionResponse:
    try:
        session = auth.login(payload.email, payload.password)
    except InvalidCredentials as error:
        raise _error(status.HTTP_401_UNAUTHORIZED, "invalid_credentials", str(error)) from error

    _set_session_cookie(response, settings, session)
    return SessionResponse(
        account=AccountResponse.from_account(session.account),
        expires_at=session.expires_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    auth: Auth,
    settings: Settings,
    token: Annotated[str | None, Depends(session_token)],
) -> None:
    """Idempotent: signing out without a session still clears the cookie."""
    if token:
        auth.logout(token)
    # Headers set on the injected response are merged into the 204.
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get("/me", response_model=AccountResponse)
async def me(account: CurrentAccount) -> AccountResponse:
    return AccountResponse.from_account(account)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    response: Response,
    account: CurrentAccount,
    auth: Auth,
    settings: Settings,
) -> None:
    """Permanently removes the signed-in account and clears the session cookie."""
    auth.delete_account(account.account_id)
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
