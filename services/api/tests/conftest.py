"""Shared pytest fixtures for authentication tests."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

# Prefect reads PREFECT_HOME at first import. Point it at the repo before
# reporting tests pull in prefect.testing / the pipeline flow.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PREFECT_HOME = _REPO_ROOT / ".prefect"
_PREFECT_HOME.mkdir(parents=True, exist_ok=True)
(_PREFECT_HOME / "storage").mkdir(parents=True, exist_ok=True)
os.environ["PREFECT_HOME"] = str(_PREFECT_HOME)
os.environ["PREFECT_RESULTS_LOCAL_STORAGE_PATH"] = str(_PREFECT_HOME / "storage")
os.environ.setdefault("PREFECT_CLI_PROMPT", "false")
os.environ["PREFECT_SERVER_EPHEMERAL_ENABLED"] = "true"
os.environ.pop("PREFECT_API_URL", None)
os.environ.pop("PREFECT_API_KEY", None)

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


@pytest.fixture(autouse=True)
def incidents_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    db_path = tmp_path / "incidents.json"
    monkeypatch.setenv("INCIDENTS_DB_PATH", str(db_path))
    import incidents_database

    incidents_database._db = None
    yield
    incidents_database._db = None


@pytest.fixture(autouse=True)
def isolate_inventory_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never let pytest talk to a developer Supabase/SQLite inventory file."""
    monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)


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


@pytest.fixture
def inventory_auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def inventory_client() -> Generator:
    """In-memory SQLite inventory DB for HTTP tests (no live Supabase in CI)."""
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool
    from sqlmodel import Session, SQLModel

    from app.main import app
    from inventory.database import configure_engine, get_db, reset_engine
    import inventory.models  # noqa: F401
    import telemetry.table  # noqa: F401 — create_all here does not call init_inventory_schema

    engine = configure_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_db():
        session = Session(engine, expire_on_commit=False, autoflush=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)
    SQLModel.metadata.drop_all(engine)
    reset_engine()
