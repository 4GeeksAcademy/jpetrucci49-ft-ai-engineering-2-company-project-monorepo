"""Pydantic models for authentication and user management."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    admin = "admin"
    manager = "manager"
    user = "user"


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    role: UserRole
    created_at: datetime


class UserInDB(UserPublic):
    hashed_password: str


class ProfilePublic(BaseModel):
    id: int
    user_id: int
    name: str
    phone: str | None = None
    address: str | None = None


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class UserRegistrationResponse(BaseModel):
    user: UserPublic
    profile: ProfilePublic


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    role: UserRole | None = None
    is_active: bool | None = None


class ProfileUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthMe(BaseModel):
    email: EmailStr
    role: UserRole
    profile: ProfilePublic


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class MessageResponse(BaseModel):
    message: str


class ChangePasswordResponse(BaseModel):
    message: str


class PasswordResetTokenInDB(BaseModel):
    id: int
    user_id: int
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime
