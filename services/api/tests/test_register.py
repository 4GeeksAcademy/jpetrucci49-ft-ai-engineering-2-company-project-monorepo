"""Tests for POST /users registration logic."""

import pytest
from auth.models import UserRegister, UserRole
from auth.security import verify_password
from auth.services import users as user_service
from pydantic import ValidationError


def test_u1_valid_registration_creates_user_and_profile():
    result = user_service.create_user(
        UserRegister(email="new@example.com", password="securepass123", name="New User")
    )
    assert result.user.email == "new@example.com"
    assert result.user.role == UserRole.user
    assert result.profile.user_id == result.user.id
    stored = user_service.get_user_by_id(result.user.id)
    assert stored is not None
    assert stored.hashed_password != "securepass123"
    assert verify_password("securepass123", stored.hashed_password)


def test_u2_default_name_from_email_local_part():
    result = user_service.create_user(
        UserRegister(email="localpart@example.com", password="securepass123")
    )
    assert result.profile.name == "localpart"


def test_u3_email_is_normalised_on_register():
    result = user_service.create_user(
        UserRegister(email="  MixedCase@Example.COM  ", password="securepass123")
    )
    assert result.user.email == "mixedcase@example.com"


def test_u4_duplicate_email_raises():
    user_service.create_user(UserRegister(email="dup@example.com", password="securepass123"))
    with pytest.raises(ValueError, match="already exists"):
        user_service.create_user(UserRegister(email="dup@example.com", password="otherpass123"))


def test_u5_password_too_short_rejected_by_model():
    with pytest.raises(ValidationError):
        UserRegister(email="short@example.com", password="short")
