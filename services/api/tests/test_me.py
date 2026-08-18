"""Tests for GET /auth/me logic (token → user → profile)."""

import pytest
from auth.dependencies import get_current_user
from auth.models import UserRole
from auth.services import profiles as profile_service
from auth.services import users as user_service
from auth.security import create_access_token, decode_access_token
from fastapi import HTTPException
import jwt
from auth.config import get_jwt_secret
from auth.security import ALGORITHM
from datetime import datetime, timedelta, timezone


async def test_m1_valid_token_loads_user_and_profile(auth_token, registered_user):
    user, profile = registered_user
    current = await get_current_user(auth_token)
    assert current.email == user.email
    loaded = profile_service.get_profile_by_user_id(current.id)
    assert loaded is not None
    assert loaded.id == profile.id


async def test_m2_role_change_in_db_visible_with_same_token(registered_user):
    user, _ = registered_user
    token = create_access_token(user.id)
    from auth.database import get_users_table

    get_users_table().update({"role": UserRole.admin.value}, doc_ids=[user.id])
    current = await get_current_user(token)
    assert current.role == UserRole.admin


async def test_m3_malformed_jwt_rejected():
    with pytest.raises(HTTPException) as exc:
        await get_current_user("not-a-valid-jwt")
    assert exc.value.status_code == 401


async def test_m4_deleted_user_with_valid_token_rejected(registered_user):
    user, _ = registered_user
    token = create_access_token(user.id)
    user_service.delete_user(user.id)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token)
    assert exc.value.status_code == 401


async def test_m5_missing_profile_returns_none_for_lookup(registered_user):
    user, profile = registered_user
    from auth.database import get_profiles_table

    get_profiles_table().remove(doc_ids=[profile.id])
    assert profile_service.get_profile_by_user_id(user.id) is None


def test_m3b_expired_token_decode_fails():
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        get_jwt_secret(),
        algorithm=ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(expired)
