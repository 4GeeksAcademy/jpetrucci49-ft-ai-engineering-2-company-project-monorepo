"""Password hashing, JWT helpers, and reset-token utilities."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from auth.config import get_access_token_expire_minutes, get_jwt_secret

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=get_access_token_expire_minutes())
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
    return int(payload["sub"])


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


__all__ = [
    "ALGORITHM",
    "InvalidTokenError",
    "create_access_token",
    "decode_access_token",
    "generate_reset_token",
    "hash_password",
    "hash_reset_token",
    "verify_password",
]
