"""Tests for the JWT authentication service."""

from datetime import datetime, timedelta, UTC

import jwt
import pytest

from backend.services.auth_service import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)

TEST_SECRET = "test-secret-key-for-testing-minimum-32-bytes!"
TEST_ALGORITHM = "HS256"


@pytest.fixture(autouse=True)
def _mock_jwt_settings(monkeypatch):
    """Patch JWT settings so tests don't depend on .env."""
    monkeypatch.setattr(
        "backend.services.auth_service.settings.jwt_secret", TEST_SECRET
    )
    monkeypatch.setattr(
        "backend.services.auth_service.settings.jwt_algorithm", TEST_ALGORITHM
    )
    monkeypatch.setattr(
        "backend.services.auth_service.settings.jwt_access_expiry_minutes", 480
    )
    monkeypatch.setattr(
        "backend.services.auth_service.settings.jwt_refresh_expiry_days", 7
    )


# --- Password hashing ---


def test_hash_password_returns_bcrypt_hash():
    """Hashed password should start with the bcrypt $2b$ prefix."""
    result = hash_password("my-secret-password")
    assert result.startswith("$2b$")


def test_verify_password_correct():
    """Correct password should verify successfully."""
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed) is True


def test_verify_password_incorrect():
    """Wrong password should fail verification."""
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("wrong-password", hashed) is False


# --- Access tokens ---


def test_create_access_token_contains_claims():
    """Access token should contain sub, email, role, and type claims."""
    token = create_access_token("user-123", "alice@example.com", role="admin")
    payload = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
    assert payload["sub"] == "user-123"
    assert payload["email"] == "alice@example.com"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_create_access_token_expiry():
    """Access token expiry should be approximately 8 hours from now."""
    token = create_access_token("user-123", "alice@example.com")
    payload = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    expected = datetime.now(UTC) + timedelta(minutes=480)
    # Allow 30 seconds of drift for test execution time
    assert abs((exp - expected).total_seconds()) < 30


# --- Refresh tokens ---


def test_create_refresh_token_contains_claims():
    """Refresh token should contain sub and type claims."""
    token = create_refresh_token("user-456")
    payload = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"
    assert "exp" in payload
    assert "iat" in payload


def test_create_refresh_token_expiry():
    """Refresh token expiry should be approximately 7 days from now."""
    token = create_refresh_token("user-456")
    payload = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    expected = datetime.now(UTC) + timedelta(days=7)
    # Allow 30 seconds of drift for test execution time
    assert abs((exp - expected).total_seconds()) < 30


# --- Token verification ---


def test_verify_token_valid():
    """A freshly created token should verify and return correct payload."""
    token = create_access_token("user-789", "bob@example.com", role="user")
    payload = verify_token(token)
    assert payload["sub"] == "user-789"
    assert payload["email"] == "bob@example.com"
    assert payload["role"] == "user"
    assert payload["type"] == "access"


def test_verify_token_expired():
    """An expired token should raise ExpiredSignatureError."""
    expired_payload = {
        "sub": "user-000",
        "type": "access",
        "iat": datetime.now(UTC) - timedelta(hours=10),
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    token = jwt.encode(expired_payload, TEST_SECRET, algorithm=TEST_ALGORITHM)
    with pytest.raises(jwt.ExpiredSignatureError):
        verify_token(token)



def test_verify_token_wrong_type():
    """A refresh token must not pass access token verification."""
    token = create_refresh_token("user-789")
    with pytest.raises(jwt.InvalidTokenError, match="Expected token type"):
        verify_token(token, expected_type="access")


def test_verify_refresh_token_accepts_refresh():
    """verify_token with expected_type='refresh' accepts a refresh token."""
    token = create_refresh_token("user-789")
    payload = verify_token(token, expected_type="refresh")
    assert payload["sub"] == "user-789"
    assert payload["type"] == "refresh"

def test_verify_token_invalid():
    """A garbage string should raise InvalidTokenError."""
    with pytest.raises(jwt.InvalidTokenError):
        verify_token("not-a-valid-jwt-token")
