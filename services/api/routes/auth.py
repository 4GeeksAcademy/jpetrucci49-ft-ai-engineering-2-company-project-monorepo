"""Authentication routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from auth.dependencies import get_current_user
from auth.models import (
    AuthMe,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    Token,
    UserPublic,
)
from auth.security import create_access_token, verify_password
from auth.services import password_reset as password_reset_service
from auth.services import profiles as profile_service
from auth.services import users as user_service

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_FAILED_MESSAGE = "Incorrect email or password."
CHANGE_PASSWORD_SUCCESS_MESSAGE = "Password updated successfully."


@router.post("/login", response_model=Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """Validate credentials and return a bearer JWT (OAuth2 password flow for /docs)."""
    user = user_service.get_user_by_email(form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=LOGIN_FAILED_MESSAGE,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=LOGIN_FAILED_MESSAGE,
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)
    return Token(access_token=token)


@router.get("/me", response_model=AuthMe)
def read_current_user(
    current_user: Annotated[UserPublic, Depends(get_current_user)],
) -> AuthMe:
    profile = profile_service.get_profile_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

    return AuthMe(email=current_user.email, role=current_user.role, profile=profile)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest) -> MessageResponse:
    password_reset_service.request_password_reset(payload.email)
    return MessageResponse(message=password_reset_service.FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest) -> MessageResponse:
    try:
        password_reset_service.reset_password(payload.token, payload.new_password)
    except password_reset_service.InvalidResetTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return MessageResponse(message=password_reset_service.RESET_SUCCESS_MESSAGE)


@router.post("/change-password", response_model=ChangePasswordResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[UserPublic, Depends(get_current_user)],
) -> ChangePasswordResponse:
    try:
        user_service.change_password(
            current_user.id,
            payload.current_password,
            payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ChangePasswordResponse(message=CHANGE_PASSWORD_SUCCESS_MESSAGE)
