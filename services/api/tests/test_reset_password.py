"""Tests for POST /auth/reset-password logic."""

from datetime import datetime, timedelta, timezone

import pytest
from auth.database import get_password_reset_tokens_table
from auth.models import UserUpdate
from auth.security import generate_reset_token, hash_reset_token, verify_password
from auth.services import password_reset as password_reset_service
from auth.services import users as user_service


def test_r1_valid_token_updates_password_and_marks_used(mock_reset_email, registered_user):
    user, _ = registered_user
    raw = password_reset_service.create_reset_token(user.id)
    password_reset_service.reset_password(raw, "newsecurepass123")
    updated = user_service.get_user_by_id(user.id)
    assert updated is not None
    assert verify_password("newsecurepass123", updated.hashed_password)
    row = get_password_reset_tokens_table().all()[0]
    assert row["used_at"] is not None


def test_r2_minimum_length_password_accepted(mock_reset_email, registered_user):
    user, _ = registered_user
    raw = password_reset_service.create_reset_token(user.id)
    password_reset_service.reset_password(raw, "12345678")
    updated = user_service.get_user_by_id(user.id)
    assert updated is not None
    assert verify_password("12345678", updated.hashed_password)


def test_r3_reused_token_rejected(mock_reset_email, registered_user):
    user, _ = registered_user
    raw = password_reset_service.create_reset_token(user.id)
    password_reset_service.reset_password(raw, "newsecurepass123")
    with pytest.raises(password_reset_service.InvalidResetTokenError):
        password_reset_service.reset_password(raw, "anotherpass123")


def test_r4_expired_token_rejected(mock_reset_email, registered_user):
    user, _ = registered_user
    raw = generate_reset_token()
    table = get_password_reset_tokens_table()
    now = datetime.now(timezone.utc)
    doc_id = table.insert(
        {
            "user_id": user.id,
            "token_hash": hash_reset_token(raw),
            "expires_at": (now - timedelta(minutes=1)).isoformat(),
            "used_at": None,
            "created_at": now.isoformat(),
        }
    )
    table.update({"id": doc_id}, doc_ids=[doc_id])
    with pytest.raises(password_reset_service.InvalidResetTokenError):
        password_reset_service.reset_password(raw, "newsecurepass123")


def test_r5_garbage_token_rejected():
    with pytest.raises(password_reset_service.InvalidResetTokenError):
        password_reset_service.reset_password("totally-invalid-token", "newsecurepass123")


def test_r6_inactive_user_token_rejected(mock_reset_email, registered_user):
    user, _ = registered_user
    raw = password_reset_service.create_reset_token(user.id)
    user_service.update_user(user.id, UserUpdate(is_active=False), allow_role_change=False)
    with pytest.raises(password_reset_service.InvalidResetTokenError):
        password_reset_service.reset_password(raw, "newsecurepass123")
