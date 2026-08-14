"""Auth-related environment configuration."""

from __future__ import annotations

import os


def _is_test_environment() -> bool:
    return os.getenv("HEALTHCORE_API_TEST", "").strip().lower() in {"1", "true", "yes"}


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "JWT_SECRET is not set. Copy services/api/.env.example to .env and set a secret."
        )
    return secret


def get_access_token_expire_minutes() -> int:
    raw = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30").strip()
    try:
        minutes = int(raw)
    except ValueError as exc:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer.") from exc
    if minutes <= 0:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero.")
    return minutes


def get_reset_token_expire_minutes() -> int:
    raw = os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "30").strip()
    try:
        minutes = int(raw)
    except ValueError as exc:
        raise RuntimeError("RESET_TOKEN_EXPIRE_MINUTES must be an integer.") from exc
    if minutes < 15 or minutes > 60:
        raise RuntimeError("RESET_TOKEN_EXPIRE_MINUTES must be between 15 and 60 (inclusive).")
    return minutes


def get_password_reset_url() -> str:
    url = os.getenv("PASSWORD_RESET_URL", "").strip()
    if not url:
        raise RuntimeError(
            "PASSWORD_RESET_URL is not set. Example: http://localhost:3001/reset-password"
        )
    return url.rstrip("/")


def get_resend_api_key() -> str:
    return os.getenv("RESEND_API_KEY", "").strip()


def get_resend_from_email() -> str:
    return os.getenv("RESEND_FROM_EMAIL", "").strip()


def validate_password_reset_config() -> None:
    """Fail fast when password-reset env is incomplete (skipped in test mode)."""
    if _is_test_environment():
        return

    get_password_reset_url()
    get_reset_token_expire_minutes()

    if not get_resend_api_key():
        raise RuntimeError("RESEND_API_KEY is required for password reset emails.")
    if not get_resend_from_email():
        raise RuntimeError("RESEND_FROM_EMAIL is required for password reset emails.")
