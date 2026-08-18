"""Shared pytest fixtures for authentication tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import auth.database as auth_database
import database as suppliers_database
import pytest
from auth.models import UserRegister, UserRole, UserUpdate
from auth.security import create_access_token, verify_password
from auth.services import users as user_service


@pytest.fixture(autouse=True)
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HEALTHCORE_API_TEST", "1")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-unit-testsie")
    monkeypatch.setenv("RESET_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("PASSWORD_RESET_URL", "http://localhost:3001/reset-password")


@pytest.fixture(autouse=True)
def suppliers_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    db_path = tmp_path / "suppliers.json"
    monkeypatch.setenv("SUPPLIERS_DB_PATH", str(db_path))
    suppliers_database._db = None
    yield
    suppliers_database._db = None


@pytest.fixture(autouse=True)
def auth_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    db_path = tmp_path / "auth.json"
    monkeypatch.setenv("AUTH_DB_PATH", str(db_path))
    auth_database._db = None
    yield
    auth_database._db = None


@pytest.fixture
def mock_reset_email():
    with patch("auth.services.password_reset.send_password_reset_email") as mocked:
        yield mocked


@pytest.fixture
def registered_user():
    payload = UserRegister(
        email="user@example.com",
        password="securepass123",
        name="Test User",
    )
    result = user_service.create_user(payload)
    user = user_service.get_user_by_id(result.user.id)
    assert user is not None
    return user, result.profile


@pytest.fixture
def admin_user():
    result = user_service.create_user(
        UserRegister(email="admin@example.com", password="adminpass123", name="Admin User")
    )
    from auth.database import get_users_table

    get_users_table().update({"role": UserRole.admin.value}, doc_ids=[result.user.id])
    user = user_service.get_user_by_id(result.user.id)
    assert user is not None
    return user, result.profile


@pytest.fixture
def second_user():
    result = user_service.create_user(
        UserRegister(email="other@example.com", password="otherpass123", name="Other")
    )
    user = user_service.get_user_by_id(result.user.id)
    assert user is not None
    return user, result.profile


@pytest.fixture
def inactive_user(registered_user):
    user, profile = registered_user
    user_service.update_user(user.id, UserUpdate(is_active=False), allow_role_change=False)
    updated = user_service.get_user_by_id(user.id)
    assert updated is not None
    return updated, profile


@pytest.fixture
def auth_token(registered_user):
    user, _ = registered_user
    return create_access_token(user.id)


def try_login(email: str, password: str) -> str | None:
    """Mirror login business rules without HTTP."""
    user = user_service.get_user_by_email(email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return create_access_token(user.id)
