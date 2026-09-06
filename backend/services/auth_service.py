"""JWT authentication service for CR8.

Handles token creation/verification and password hashing using
PyJWT and bcrypt. Access tokens (8hr) are sent via Bearer header,
refresh tokens (7d) are stored in httpOnly cookies.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, UTC

import bcrypt
import jwt

from backend.config import settings

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash string.
    """
    logger.info("Hashing password")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        password: The plaintext password to check.
        hashed: The bcrypt hash to compare against.

    Returns:
        True if the password matches the hash.
    """
    logger.info("Verifying password")
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str, role: str = "user") -> str:
    """Create a JWT access token.

    Args:
        user_id: The user's UUID string.
        email: The user's email address.
        role: The user's role (default: "user").

    Returns:
        Encoded JWT access token string.
    """
    logger.info("Creating access token for user_id=%s", user_id)
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_expiry_minutes),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    logger.info(
        "Access token created for user_id=%s, expires_in=%d min",
        user_id,
        settings.jwt_access_expiry_minutes,
    )
    return token


def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token.

    Args:
        user_id: The user's UUID string.

    Returns:
        Encoded JWT refresh token string.
    """
    logger.info("Creating refresh token for user_id=%s", user_id)
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_expiry_days),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    logger.info(
        "Refresh token created for user_id=%s, expires_in=%d days",
        user_id,
        settings.jwt_refresh_expiry_days,
    )
    return token


def generate_password_reset_token() -> str:
    """Generate a cryptographically secure, opaque password-reset token.

    The raw token is emailed to the user; only its SHA-256 hash is stored.

    Returns:
        A URL-safe random token string (~256 bits of entropy).
    """
    logger.info("Generating password reset token")
    return secrets.token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    """Hash a password-reset token for storage.

    Reset tokens are high-entropy random values, so a plain SHA-256 digest
    (no bcrypt salt) is sufficient and lets us look tokens up by hash.

    Args:
        token: The raw reset token string.

    Returns:
        Hex-encoded SHA-256 digest of the token.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(token: str, expected_type: str = "access") -> dict:
    """Verify and decode a JWT token, enforcing the token type claim.

    Args:
        token: The JWT token string to verify.
        expected_type: Required value of the ``type`` claim (default: "access").

    Returns:
        The decoded token payload as a dict.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is invalid or type mismatches.
    """
    logger.info("Verifying token (expected_type=%s)", expected_type)
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != expected_type:
            logger.warning(
                "Token type mismatch: expected=%s, got=%s",
                expected_type,
                payload.get("type"),
            )
            raise jwt.InvalidTokenError(
                f"Expected token type \'{expected_type}\'"
            )
        logger.info("Token verified successfully for sub=%s", payload.get("sub"))
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: expired")
        raise
    except jwt.InvalidTokenError:
        logger.warning("Token verification failed: invalid")
        raise
