"""Tests for POST /auth/login credential logic."""

from tests.conftest import try_login


def test_l1_valid_credentials_return_decodable_token(registered_user):
    user, _ = registered_user
    token = try_login(user.email, "securepass123")
    assert token is not None

    from auth.security import decode_access_token

    assert decode_access_token(token) == user.id


def test_l2_mixed_case_email_lookup_after_lowercase_register():
    from auth.models import UserRegister
    from auth.services import users as user_service

    user_service.create_user(UserRegister(email="mixed@example.com", password="securepass123"))
    token = try_login("Mixed@Example.com", "securepass123")
    assert token is not None


def test_l3_wrong_password_does_not_issue_token(registered_user):
    user, _ = registered_user
    assert try_login(user.email, "wrongpassword") is None


def test_l4_unknown_email_does_not_issue_token():
    assert try_login("missing@example.com", "securepass123") is None


def test_l5_inactive_user_cannot_login(inactive_user):
    user, _ = inactive_user
    assert try_login(user.email, "securepass123") is None
