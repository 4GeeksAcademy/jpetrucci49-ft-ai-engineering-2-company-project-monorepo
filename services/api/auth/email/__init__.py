"""Transactional email delivery for auth flows (Resend)."""

from __future__ import annotations

from functools import lru_cache

from auth.email.resend_sender import ResendPasswordResetSender


@lru_cache(maxsize=1)
def get_password_reset_sender() -> ResendPasswordResetSender:
    return ResendPasswordResetSender()


def send_password_reset_email(*, to_email: str, reset_link: str, expires_minutes: int) -> None:
    get_password_reset_sender().send_password_reset_email(
        to_email=to_email,
        reset_link=reset_link,
        expires_minutes=expires_minutes,
    )
