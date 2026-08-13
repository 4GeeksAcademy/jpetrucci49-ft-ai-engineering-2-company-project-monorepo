"""Password reset token lifecycle and orchestration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from auth.config import get_password_reset_url, get_reset_token_expire_minutes
from auth.database import get_password_reset_tokens_table
from auth.email import send_password_reset_email
from auth.models import PasswordResetTokenInDB
from auth.security import generate_reset_token, hash_reset_token
from auth.services import users as user_service
from tinydb import Query

logger = logging.getLogger(__name__)

FORGOT_PASSWORD_MESSAGE = (
    "If that address is registered, you'll receive a link shortly."
)
INVALID_RESET_TOKEN_MESSAGE = "Invalid or expired reset token."
RESET_SUCCESS_MESSAGE = "Password reset successfully."


class InvalidResetTokenError(Exception):
    """Raised when a reset token cannot be consumed."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _to_reset_token(document: dict) -> PasswordResetTokenInDB:
    return PasswordResetTokenInDB.model_validate(document)


def _invalidate_unused_tokens_for_user(user_id: int) -> None:
    table = get_password_reset_tokens_table()
    now = _utc_now().isoformat()
    matches = table.search(
        (Query().user_id == user_id) & (Query().used_at.test(lambda value: value is None))
    )
    for document in matches:
        doc_id = document.get("id")
        if doc_id is not None:
            table.update({"used_at": now}, doc_ids=[doc_id])


def create_reset_token(user_id: int) -> str:
    """Create a single-use reset token and return the raw secret for the email link."""
    _invalidate_unused_tokens_for_user(user_id)

    raw_token = generate_reset_token()
    token_hash = hash_reset_token(raw_token)
    now = _utc_now()
    expires_at = now + timedelta(minutes=get_reset_token_expire_minutes())

    table = get_password_reset_tokens_table()
    document = {
        "user_id": user_id,
        "token_hash": token_hash,
        "expires_at": expires_at.isoformat(),
        "used_at": None,
        "created_at": now.isoformat(),
    }
    doc_id = table.insert(document)
    table.update({"id": doc_id}, doc_ids=[doc_id])
    return raw_token


def find_valid_token(raw_token: str) -> PasswordResetTokenInDB | None:
    token_hash = hash_reset_token(raw_token)
    table = get_password_reset_tokens_table()
    matches = table.search(Query().token_hash == token_hash)
    if not matches:
        return None

    token = _to_reset_token(matches[0])
    if token.used_at is not None:
        return None
    if token.expires_at <= _utc_now():
        return None
    return token


def _build_reset_link(raw_token: str) -> str:
    base_url = get_password_reset_url()
    query = urlencode({"token": raw_token})
    return f"{base_url}?{query}"


def request_password_reset(email: str) -> None:
    """Issue a reset email when the account exists; otherwise no-op (no enumeration)."""
    user = user_service.get_user_by_email(email)
    if user is None or not user.is_active:
        return

    raw_token = create_reset_token(user.id)
    reset_link = _build_reset_link(raw_token)
    expires_minutes = get_reset_token_expire_minutes()

    try:
        send_password_reset_email(
            to_email=user.email,
            reset_link=reset_link,
            expires_minutes=expires_minutes,
        )
    except Exception:
        logger.exception(
            "Failed to send password reset email for user_id=%s",
            user.id,
        )


def reset_password(raw_token: str, new_password: str) -> None:
    token = find_valid_token(raw_token)
    if token is None:
        raise InvalidResetTokenError(INVALID_RESET_TOKEN_MESSAGE)

    user = user_service.get_user_by_id(token.user_id)
    if user is None or not user.is_active:
        raise InvalidResetTokenError(INVALID_RESET_TOKEN_MESSAGE)

    user_service.update_password(token.user_id, new_password)

    table = get_password_reset_tokens_table()
    table.update({"used_at": _utc_now().isoformat()}, doc_ids=[token.id])
    _invalidate_unused_tokens_for_user(token.user_id)
