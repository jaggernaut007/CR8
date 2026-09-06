"""Tests for backend/services/email_service.py.

Verifies Resend delivery and the dev-log fallback. No real network calls —
``requests.post`` is mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.config import settings
from backend.services import email_service


@pytest.fixture(autouse=True)
def _reset_email_settings(monkeypatch):
    """Ensure Resend is not configured for each test."""
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(settings, "resend_from_email", "")


class TestResend:
    def test_sends_via_resend_when_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
        monkeypatch.setattr(settings, "resend_from_email", "CR8 <no-reply@cr8.dev>")

        with patch("backend.services.email_service.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {"id": "msg_123"}
            mock_post.return_value = mock_resp

            result = email_service.send_password_reset_email(
                "user@example.com",
                "http://localhost:8080/reset-password?token=abc",
            )

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer re_test_key"
        assert call_kwargs["json"]["from"] == "CR8 <no-reply@cr8.dev>"
        assert call_kwargs["json"]["to"] == ["user@example.com"]
        assert call_kwargs["json"]["subject"] == "Reset your CR8 password"
        assert "reset-password?token=abc" in call_kwargs["json"]["text"]

    def test_resend_failure_returns_false(self, monkeypatch):
        monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
        monkeypatch.setattr(settings, "resend_from_email", "CR8 <no-reply@cr8.dev>")

        with patch("backend.services.email_service.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = Exception("500 Internal Server Error")
            mock_post.return_value = mock_resp

            result = email_service.send_password_reset_email(
                "user@example.com", "http://localhost:8080/reset"
            )

        assert result is False


class TestDevFallback:
    def test_no_provider_logs_and_returns_true(self):
        """With no Resend configured, the email is logged (dev mode)."""
        result = email_service.send_password_reset_email(
            "user@example.com", "http://localhost:8080/reset"
        )
        assert result is True
