"""Tests for /users admin and self-service logic."""

import pytest
from auth.dependencies import require_admin, require_self_or_admin
from auth.models import UserPublic, UserRole, UserUpdate
from auth.services import users as user_service
from fastapi import HTTPException


def test_a1_admin_lists_users_sorted(admin_user, registered_user):
    users = user_service.list_users()
    emails = [user.email for user in users]
    assert emails == sorted(emails)
    assert len(users) >= 2


def test_a2_empty_database_returns_empty_list():
    assert user_service.list_users() == []


async def test_a3_non_admin_cannot_pass_require_admin(registered_user):
    user, _ = registered_user
    current = UserPublic.model_validate(user.model_dump())
    with pytest.raises(HTTPException) as exc:
        await require_admin(current)
    assert exc.value.status_code == 403


def test_g1_user_can_read_own_record(registered_user):
    user, _ = registered_user
    loaded = user_service.get_user_by_id(user.id)
    assert loaded is not None
    public = UserPublic.model_validate(loaded.model_dump())
    assert public.email == user.email


def test_g2_admin_can_read_other_user(admin_user, second_user):
    admin, _ = admin_user
    other, _ = second_user
    loaded = user_service.get_user_by_id(other.id)
    assert loaded is not None
    assert loaded.email == other.email
    assert admin.id != other.id


async def test_g3_non_admin_cannot_access_other_user(registered_user, second_user):
    user, _ = registered_user
    other, _ = second_user
    current = UserPublic.model_validate(user.model_dump())
    with pytest.raises(HTTPException) as exc:
        await require_self_or_admin(other.id, current)
    assert exc.value.status_code == 403


def test_g4_missing_user_returns_none():
    assert user_service.get_user_by_id(424242) is None


def test_p1_self_email_update_is_normalised(registered_user):
    user, _ = registered_user
    updated = user_service.update_user(
        user.id,
        UserUpdate(email="  Updated@Example.com  "),
        allow_role_change=False,
    )
    assert updated.email == "updated@example.com"


def test_p2_admin_can_change_role(admin_user, second_user):
    _, _ = admin_user
    other, _ = second_user
    updated = user_service.update_user(
        other.id,
        UserUpdate(role=UserRole.manager),
        allow_role_change=True,
    )
    assert updated.role == UserRole.manager


def test_p3_empty_update_returns_existing_user(registered_user):
    user, _ = registered_user
    updated = user_service.update_user(user.id, UserUpdate(), allow_role_change=False)
    assert updated.email == user.email


def test_p4_non_admin_cannot_change_role(registered_user):
    user, _ = registered_user
    with pytest.raises(PermissionError, match="Only admins"):
        user_service.update_user(
            user.id,
            UserUpdate(role=UserRole.admin),
            allow_role_change=False,
        )


def test_p5_duplicate_email_on_update_rejected(registered_user, second_user):
    user, _ = registered_user
    other, _ = second_user
    with pytest.raises(ValueError, match="already exists"):
        user_service.update_user(
            user.id,
            UserUpdate(email=other.email),
            allow_role_change=False,
        )


async def test_p6_non_admin_cannot_update_other_user_via_dependency(registered_user, second_user):
    user, _ = registered_user
    other, _ = second_user
    current = UserPublic.model_validate(user.model_dump())
    with pytest.raises(HTTPException) as exc:
        await require_self_or_admin(other.id, current)
    assert exc.value.status_code == 403


def test_d1_self_delete_removes_user_and_profile(registered_user):
    user, profile = registered_user
    from auth.services import profiles as profile_service

    user_service.delete_user(user.id)
    assert user_service.get_user_by_id(user.id) is None
    assert profile_service.get_profile_by_user_id(user.id) is None


def test_d2_admin_deletes_other_user(admin_user, second_user):
    _, _ = admin_user
    other, _ = second_user
    user_service.delete_user(other.id)
    assert user_service.get_user_by_id(other.id) is None


async def test_d3_non_admin_cannot_delete_other_user(registered_user, second_user):
    user, _ = registered_user
    other, _ = second_user
    current = UserPublic.model_validate(user.model_dump())
    with pytest.raises(HTTPException) as exc:
        await require_self_or_admin(other.id, current)
    assert exc.value.status_code == 403


def test_d4_delete_missing_user_raises():
    with pytest.raises(LookupError, match="User not found"):
        user_service.delete_user(99999)
