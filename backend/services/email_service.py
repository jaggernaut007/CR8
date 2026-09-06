"""Outbound email service for CR8.

Sends transactional email (currently password-reset links) through Resend, with
a development fallback that logs the message when Resend is not configured.
All outbound email is isolated here so callers never touch Resend directly and
tests can mock this module.

Resend is configured through ``RESEND_API_KEY`` and ``RESEND_FROM_EMAIL``.
When they are empty, messages are logged at INFO instead of being delivered.
"""

import logging

import requests

from backend.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _resend_configured() -> bool:
    """Return True when Resend delivery is enabled via settings."""
    return bool(settings.resend_api_key and settings.resend_from_email)


def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    """Send a password-reset email, or log it when Resend is not configured.

    Args:
        to_email: Recipient email address.
        reset_link: The reset URL the user should open.

    Returns:
        True when the email was sent (or logged in dev mode), False on
        delivery failure.
    """
    subject = "Reset your CR8 password"
    body = (
        f"Hello,\n\n"
        f"We received a request to reset your CR8 password.\n\n"
        f"To reset your password, open this link (valid for "
        f"{settings.password_reset_token_ttl_minutes} minutes):\n"
        f"{reset_link}\n\n"
        f"If you didn't request this, you can safely ignore this email.\n"
    )

    if not _resend_configured():
        logger.info(
            "Resend not configured — password reset link for %s: %s",
            to_email,
            reset_link,
        )
        return True

    try:
        resp = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.resend_from_email,
                "to": [to_email],
                "subject": subject,
                "text": body,
            },
            timeout=10,
        )
        resp.raise_for_status()
        message_id = resp.json().get("id", "unknown")
        logger.info(
            "Password reset email sent via Resend to %s (id=%s)", to_email, message_id
        )
        return True
    except Exception:
        logger.exception("Failed to send password reset email via Resend to %s", to_email)
        return False

