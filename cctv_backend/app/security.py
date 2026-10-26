"""
Security primitives:
- Argon2id password hashing (via argon2-cffi directly).
- JWT access/refresh token creation and verification.

Why not passlib? passlib is unmaintained and imports Python's stdlib
`crypt` module, which was REMOVED in Python 3.13 - so it crashes on
modern Python. argon2-cffi is the library passlib was wrapping for
Argon2 anyway, so we use it directly. Same algorithm, same security,
one less broken dependency.

Note: HTTPS/TLS 1.3 termination happens at the reverse proxy / server
config (e.g. nginx, uvicorn --ssl-*), not in this file - but every
endpoint here assumes it is only ever reached over TLS in production.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.config import settings

# Argon2id specifically (Type.ID) - resistant to both side-channel and
# GPU-cracking attacks. These are the OWASP-recommended parameters.
_hasher = PasswordHasher(
    time_cost=3,        # iterations
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,       # Argon2id
)


def hash_password(plain_password: str) -> str:
    """Returns an encoded Argon2id hash string (includes salt + params)."""
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time verification. Returns False instead of raising on mismatch."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    True if the stored hash used weaker parameters than we now use
    (e.g. after you raise time_cost). Call after a successful login and
    re-hash the password if it returns True.
    """
    try:
        return _hasher.check_needs_rehash(hashed_password)
    except InvalidHashError:
        return False


def _create_token(subject: str, role: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(username: str, role: str) -> str:
    return _create_token(
        username, role,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(username: str, role: str) -> str:
    return _create_token(
        username, role,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None