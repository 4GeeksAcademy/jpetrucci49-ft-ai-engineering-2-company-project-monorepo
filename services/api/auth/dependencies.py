"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from auth.models import UserPublic, UserRole
from auth.security import decode_access_token
from auth.services import users as user_service
from jwt.exceptions import InvalidTokenError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

INVALID_CREDENTIALS_MESSAGE = "Could not validate credentials."


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserPublic:
    try:
        user_id = decode_access_token(token)
    except (InvalidTokenError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE,
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = user_service.get_user_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserPublic.model_validate(user.model_dump(exclude={"hashed_password"}))


async def require_admin(
    current_user: Annotated[UserPublic, Depends(get_current_user)],
) -> UserPublic:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


async def require_self_or_admin(
    user_id: int,
    current_user: Annotated[UserPublic, Depends(get_current_user)],
) -> UserPublic:
    """Allow access when the caller is the target user or an admin."""
    if current_user.role != UserRole.admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this user.",
        )
    return current_user
