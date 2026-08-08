"""Session token generation.

The database stores only a SHA-256 digest of the token. A stolen database dump
therefore cannot be replayed as a live session cookie.
"""

from __future__ import annotations

import hashlib
import secrets

TOKEN_BYTES = 32


def new_session_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
