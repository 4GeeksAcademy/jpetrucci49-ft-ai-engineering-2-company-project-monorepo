"""Tests for /profiles/me logic."""

import pytest
from auth.models import ProfileUpdate, UserPublic
from auth.services import profiles as profile_service
from routes.profiles import update_my_profile
from fastapi import HTTPException


def test_pm1_user_profile_loads(registered_user):
    user, profile = registered_user
    loaded = profile_service.get_profile_by_user_id(user.id)
    assert loaded is not None
    assert loaded.name == profile.name


def test_pm2_missing_profile_returns_none(registered_user):
    user, profile = registered_user
    from auth.database import get_profiles_table

    get_profiles_table().remove(doc_ids=[profile.id])
    assert profile_service.get_profile_by_user_id(user.id) is None


def test_pu1_update_name_persisted(registered_user):
    user, _ = registered_user
    updated = profile_service.update_profile(user.id, ProfileUpdate(name="Renamed"))
    assert updated.name == "Renamed"


def test_pu2_partial_update_leaves_other_fields(registered_user):
    user, profile = registered_user
    updated = profile_service.update_profile(user.id, ProfileUpdate(phone="555-0100"))
    assert updated.phone == "555-0100"
    assert updated.name == profile.name


def test_pu3_empty_profile_update_rejected_by_route(registered_user):
    user, _ = registered_user
    current = UserPublic.model_validate(user.model_dump())
    with pytest.raises(HTTPException) as exc:
        update_my_profile(ProfileUpdate(), current)
    assert exc.value.status_code == 422


def test_pu4_update_missing_profile_raises():
    with pytest.raises(LookupError, match="Profile not found"):
        profile_service.update_profile(99999, ProfileUpdate(name="Ghost"))
