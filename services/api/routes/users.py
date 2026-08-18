"""User management routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from auth.dependencies import get_current_user, require_admin, require_self_or_admin
from auth.models import UserPublic, UserRegister, UserRegistrationResponse, UserRole, UserUpdate
from auth.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister) -> UserRegistrationResponse:
    try:
        return user_service.create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("", response_model=list[UserPublic])
def list_users(_: Annotated[UserPublic, Depends(require_admin)]) -> list[UserPublic]:
    return user_service.list_users()


@router.get("/{user_id}", response_model=UserPublic)
def get_user(
    user_id: int,
    _: Annotated[UserPublic, Depends(require_self_or_admin)],
) -> UserPublic:
    user = user_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserPublic.model_validate(user.model_dump(exclude={"hashed_password"}))


@router.put("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: Annotated[UserPublic, Depends(get_current_user)],
) -> UserPublic:
    if current_user.role != UserRole.admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to update this user.",
        )

    allow_role_change = current_user.role == UserRole.admin
    try:
        return user_service.update_user(user_id, payload, allow_role_change=allow_role_change)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    _: Annotated[UserPublic, Depends(require_self_or_admin)],
) -> Response:
    try:
        user_service.delete_user(user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
