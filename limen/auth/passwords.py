"""Password hashing on the standard library only.

scrypt ships with CPython, so a clinic can reproduce the environment from
pyproject.toml without a compiler for a C-extension KDF. Parameters are stored
inside the encoded hash, which lets them be raised later without invalidating
existing accounts.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode

ALGORITHM = "scrypt"
COST_LOG2 = 14
BLOCK_SIZE = 8
PARALLELISM = 1
KEY_LENGTH = 32
SALT_LENGTH = 16
# 128 * 2**14 * 8 = 16 MiB of working memory; the ceiling leaves headroom.
MAX_MEMORY = 64 * 1024 * 1024

MINIMUM_PASSWORD_LENGTH = 10


def _b64(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode(value + padding)


def _derive(password: str, salt: bytes, cost_log2: int, block_size: int, parallelism: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**cost_log2,
        r=block_size,
        p=parallelism,
        dklen=KEY_LENGTH,
        maxmem=MAX_MEMORY,
    )


def hash_password(password: str) -> str:
    """Encode as `scrypt$<log2 n>$<r>$<p>$<salt>$<key>`."""
    salt = secrets.token_bytes(SALT_LENGTH)
    key = _derive(password, salt, COST_LOG2, BLOCK_SIZE, PARALLELISM)
    return "$".join(
        [
            ALGORITHM,
            str(COST_LOG2),
            str(BLOCK_SIZE),
            str(PARALLELISM),
            _b64(salt),
            _b64(key),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time comparison. A malformed stored hash verifies as False."""
    try:
        algorithm, cost, block_size, parallelism, salt, expected = encoded.split("$")
        if algorithm != ALGORITHM:
            return False
        candidate = _derive(
            password,
            _unb64(salt),
            int(cost),
            int(block_size),
            int(parallelism),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, _unb64(expected))
