"""Resend transactional email sender."""

from __future__ import annotations

import resend

from auth.config import get_resend_api_key, get_resend_from_email
from auth.email.templates import build_password_reset_content


class ResendPasswordResetSender:
    def __init__(self) -> None:
        resend.api_key = get_resend_api_key()
        self._from_email = get_resend_from_email()

    def send_password_reset_email(
        self,
        *,
        to_email: str,
        reset_link: str,
        expires_minutes: int,
    ) -> None:
        subject, text, html = build_password_reset_content(
            reset_link=reset_link,
            expires_minutes=expires_minutes,
        )
        resend.Emails.send(
            {
                "from": self._from_email,
                "to": [to_email],
                "subject": subject,
                "html": html,
                "text": text,
            }
        )
