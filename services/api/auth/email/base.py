"""Email delivery abstractions for transactional messages."""

from __future__ import annotations

from typing import Protocol


class PasswordResetEmailSender(Protocol):
    def send_password_reset_email(
        self,
        *,
        to_email: str,
        reset_link: str,
        expires_minutes: int,
    ) -> None:
        """Send a password reset email with HTML and plain-text bodies."""
