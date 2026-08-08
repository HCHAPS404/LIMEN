"""Auth failures as domain errors, so transport chooses the status code."""

from __future__ import annotations


class AuthError(Exception):
    """Base class for every recoverable authentication failure."""


class InvalidEmail(AuthError):
    def __init__(self, email: str) -> None:
        super().__init__(f"{email!r} is not a usable email address.")
        self.email = email


class WeakPassword(AuthError):
    def __init__(self, minimum_length: int) -> None:
        super().__init__(f"Password must be at least {minimum_length} characters.")
        self.minimum_length = minimum_length


class EmailAlreadyRegistered(AuthError):
    def __init__(self, email: str) -> None:
        super().__init__("An account with this email already exists.")
        self.email = email


class InvalidCredentials(AuthError):
    """Raised for both unknown email and wrong password.

    The message never distinguishes the two: telling a caller which half failed
    turns the login form into an account-enumeration oracle.
    """

    def __init__(self) -> None:
        super().__init__("Email or password is incorrect.")


class SessionInvalid(AuthError):
    def __init__(self) -> None:
        super().__init__("The session is missing, expired, or revoked.")
