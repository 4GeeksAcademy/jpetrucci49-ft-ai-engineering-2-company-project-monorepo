"""Tests for POST /auth/forgot-password logic."""

from auth.database import get_password_reset_tokens_table
from auth.services import password_reset as password_reset_service
from auth.services import users as user_service


def test_f1_active_user_creates_token_and_sends_email(mock_reset_email, registered_user):
    user, _ = registered_user
    password_reset_service.request_password_reset(user.email)
    assert mock_reset_email.call_count == 1
    assert len(get_password_reset_tokens_table().all()) == 1


def test_f2_unknown_email_is_silent_no_op(mock_reset_email):
    password_reset_service.request_password_reset("unknown@example.com")
    mock_reset_email.assert_not_called()
    assert get_password_reset_tokens_table().all() == []


def test_f3_inactive_user_does_not_receive_reset(mock_reset_email, inactive_user):
    user, _ = inactive_user
    password_reset_service.request_password_reset(user.email)
    mock_reset_email.assert_not_called()
    assert get_password_reset_tokens_table().all() == []


def test_f4_email_failure_is_swallowed(mock_reset_email, registered_user):
    user, _ = registered_user
    mock_reset_email.side_effect = RuntimeError("resend down")
    password_reset_service.request_password_reset(user.email)


def test_f5_new_request_invalidates_previous_unused_token(mock_reset_email, registered_user):
    user, _ = registered_user
    first = password_reset_service.create_reset_token(user.id)
    password_reset_service.request_password_reset(user.email)
    assert password_reset_service.find_valid_token(first) is None
