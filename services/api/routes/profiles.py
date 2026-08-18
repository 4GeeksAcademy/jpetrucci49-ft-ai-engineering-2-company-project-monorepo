"""Profile routes for the authenticated user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from auth.dependencies import get_current_user
from auth.models import ProfilePublic, ProfileUpdate, UserPublic
from auth.services import profiles as profile_service

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=ProfilePublic)
def read_my_profile(
    current_user: Annotated[UserPublic, Depends(get_current_user)],
) -> ProfilePublic:
    profile = profile_service.get_profile_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return profile


@router.put("/me", response_model=ProfilePublic)
def update_my_profile(
    payload: ProfileUpdate,
    current_user: Annotated[UserPublic, Depends(get_current_user)],
) -> ProfilePublic:
    if payload.name is None and payload.phone is None and payload.address is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one profile field must be provided.",
        )

    try:
        return profile_service.update_profile(current_user.id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
