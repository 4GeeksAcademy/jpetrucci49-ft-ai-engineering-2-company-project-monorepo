"""Tests for auth/security.py JWT and password helpers."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from auth.config import get_jwt_secret
from auth.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)


def test_s1_hash_and_verify_password_round_trip():
    hashed = hash_password("securepass123")
    assert verify_password("securepass123", hashed)
    assert not verify_password("wrong", hashed)


def test_s2_access_token_decodes_to_user_id():
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_s3_reset_tokens_are_unique():
    assert generate_reset_token() != generate_reset_token()


def test_s4_expired_jwt_is_rejected():
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
        get_jwt_secret(),
        algorithm=ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(expired)


def test_s5_jwt_with_wrong_secret_is_rejected():
    token = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "wrong-secret",
        algorithm=ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_s6_reset_token_hash_is_deterministic():
    assert hash_reset_token("abc") == hash_reset_token("abc")
    assert hash_reset_token("abc") != hash_reset_token("xyz")
