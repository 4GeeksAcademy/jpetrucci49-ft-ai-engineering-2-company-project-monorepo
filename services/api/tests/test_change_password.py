"""Tests for POST /auth/change-password logic."""

import pytest
from auth.security import verify_password
from auth.services import users as user_service


def test_c1_change_password_with_correct_current(registered_user):
    user, _ = registered_user
    user_service.change_password(user.id, "securepass123", "newsecurepass123")
    updated = user_service.get_user_by_id(user.id)
    assert updated is not None
    assert verify_password("newsecurepass123", updated.hashed_password)


def test_c2_same_password_rejected(registered_user):
    user, _ = registered_user
    with pytest.raises(ValueError, match="different"):
        user_service.change_password(user.id, "securepass123", "securepass123")


def test_c3_wrong_current_password_rejected(registered_user):
    user, _ = registered_user
    with pytest.raises(ValueError, match="Current password is incorrect"):
        user_service.change_password(user.id, "wrongpass123", "newsecurepass123")


def test_c4_unknown_user_rejected():
    with pytest.raises(LookupError, match="User not found"):
        user_service.change_password(9999, "securepass123", "newsecurepass123")
