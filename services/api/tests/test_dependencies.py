"""Tests for auth dependency authorization logic."""

import pytest
from auth.dependencies import get_current_user, require_admin, require_self_or_admin
from auth.models import UserPublic, UserRole
from auth.security import create_access_token
from auth.services import users as user_service
from fastapi import HTTPException


async def test_dp1_valid_token_returns_active_user(auth_token, registered_user):
    user, _ = registered_user
    current = await get_current_user(auth_token)
    assert current.id == user.id
    assert current.is_active is True


async def test_dp2_inactive_user_rejected(inactive_user):
    user, _ = inactive_user
    token = create_access_token(user.id)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token)
    assert exc.value.status_code == 401


async def test_dp3_require_admin_passes_for_admin(admin_user):
    admin, _ = admin_user
    current = UserPublic.model_validate(admin.model_dump())
    result = await require_admin(current)
    assert result.role == UserRole.admin


async def test_dp4_require_admin_rejects_regular_user(registered_user):
    user, _ = registered_user
    current = UserPublic.model_validate(user.model_dump())
    with pytest.raises(HTTPException) as exc:
        await require_admin(current)
    assert exc.value.status_code == 403


async def test_dp5_require_self_or_admin_allows_self(registered_user):
    user, _ = registered_user
    current = UserPublic.model_validate(user.model_dump())
    result = await require_self_or_admin(user.id, current)
    assert result.id == user.id


async def test_dp6_require_self_or_admin_allows_admin_on_other(admin_user, registered_user):
    admin, _ = admin_user
    user, _ = registered_user
    current = UserPublic.model_validate(admin.model_dump())
    result = await require_self_or_admin(user.id, current)
    assert result.id == admin.id


async def test_dp7_require_self_or_admin_rejects_other_user(registered_user, second_user):
    user, _ = registered_user
    other, _ = second_user
    current = UserPublic.model_validate(user.model_dump())
    with pytest.raises(HTTPException) as exc:
        await require_self_or_admin(other.id, current)
    assert exc.value.status_code == 403
