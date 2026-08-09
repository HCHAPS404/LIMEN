"""Auth request/response bodies.

These are transport objects. They are built from `limen.auth.Account` and never
from a persistence row, so a password hash cannot reach a response.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from limen.auth import Account


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)
    display_name: str = Field(default="", max_length=80)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class AccountResponse(BaseModel):
    account_id: str
    email: str
    display_name: str
    created_at: datetime

    @classmethod
    def from_account(cls, account: Account) -> AccountResponse:
        return cls(
            account_id=account.account_id,
            email=account.email,
            display_name=account.display_name,
            created_at=account.created_at,
        )


class SessionResponse(BaseModel):
    """The session token is not part of the body: it travels as an httpOnly
    cookie, so client JavaScript can never read it."""

    account: AccountResponse
    expires_at: datetime
