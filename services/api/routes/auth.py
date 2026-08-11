"""Authentication routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from auth.dependencies import get_current_user
from auth.models import AuthMe, Token, UserPublic
from auth.security import create_access_token, verify_password
from auth.services import profiles as profile_service
from auth.services import users as user_service

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_FAILED_MESSAGE = "Incorrect email or password."


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
