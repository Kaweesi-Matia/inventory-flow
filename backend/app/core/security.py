"""
Security primitives: password hashing and JWT issuance/validation.

Passwords are never stored in plaintext — only bcrypt hashes are persisted.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt as _bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# passlib 1.7.4 looks up bcrypt.__about__.__version__, which bcrypt>=4.1 removed.
if not hasattr(_bcrypt, "__about__"):
    class _About:
        __version__ = getattr(_bcrypt, "__version__", "4.0.1")

    _bcrypt.__about__ = _About()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_claims: Optional[dict[str, Any]] = None) -> str:
    """
    Create a signed JWT access token.

    `subject` is typically the user id (as a string). `extra_claims` can
    carry non-sensitive info like role, to avoid a DB hit on every request
    for coarse-grained checks (fine-grained checks still hit the DB).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT. Raises jose.JWTError on any failure
    (expired, bad signature, malformed, etc). Callers should catch this
    and translate it into a 401.
    """
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload
