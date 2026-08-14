"""Shared email content builders."""

from __future__ import annotations


def build_password_reset_content(*, reset_link: str, expires_minutes: int) -> tuple[str, str, str]:
    subject = "HealthCore — reset your password"
    text = (
        "You requested a password reset for your HealthCore account.\n\n"
        f"Reset your password (expires in {expires_minutes} minutes):\n"
        f"{reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    html = f"""\
<!DOCTYPE html>
<html lang="en">
  <body style="margin:0;padding:24px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:16px;line-height:1.5;color:#0f172a;background:#f8fafc;">
    <div style="max-width:480px;margin:0 auto;padding:24px;background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;">
      <p style="margin:0 0 16px;font-size:18px;font-weight:600;">Reset your HealthCore password</p>
      <p style="margin:0 0 16px;">You requested a password reset. Tap the button below to choose a new password. This link expires in <strong>{expires_minutes} minutes</strong>.</p>
      <p style="margin:0 0 24px;">
        <a href="{reset_link}" style="display:inline-block;padding:12px 20px;background:#0f766e;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:600;">Reset password</a>
      </p>
      <p style="margin:0 0 8px;font-size:14px;color:#64748b;">If the button does not work, copy and paste this link into your browser:</p>
      <p style="margin:0;font-size:14px;word-break:break-all;color:#334155;">{reset_link}</p>
      <p style="margin:24px 0 0;font-size:14px;color:#64748b;">If you did not request this, you can ignore this email.</p>
    </div>
  </body>
</html>"""
    return subject, text, html
