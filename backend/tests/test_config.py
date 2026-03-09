"""Tests for backend/config.py Settings._validate_required_secrets validator.

All tests instantiate Settings directly with controlled keyword arguments.
In pydantic-settings v2, keyword args to __init__ take the highest priority
and override any values from the .env file, so the real .env on disk cannot
interfere with these assertions.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestValidateRequiredSecrets:
    """Tests for the _validate_required_secrets model_validator on Settings."""

    def _make_settings(self, **overrides):
        """Instantiate Settings with safe empty defaults, merging overrides.

        Passing keyword args directly overrides env file values in pydantic-settings v2.
        Both jwt_secret and openai_api_key default to empty string (treated as 'not set').
        """
        from backend.config import Settings

        defaults = {
            "openai_api_key": "",
            "jwt_secret": "",
        }
        defaults.update(overrides)
        return Settings(**defaults)

    # -----------------------------------------------------------------------
    # jwt_secret validation
    # -----------------------------------------------------------------------

    def test_jwt_secret_empty_string_is_allowed(self):
        """Empty jwt_secret is treated as 'not set' and must not raise."""
        settings = self._make_settings(jwt_secret="")
        assert settings.jwt_secret == ""

    def test_jwt_secret_exactly_32_chars_is_valid(self):
        """A 32-character secret is the minimum valid length."""
        secret = "a" * 32
        settings = self._make_settings(jwt_secret=secret)
        assert settings.jwt_secret == secret

    def test_jwt_secret_longer_than_32_chars_is_valid(self):
        """Secrets longer than 32 characters must always pass."""
        secret = "x" * 64
        settings = self._make_settings(jwt_secret=secret)
        assert settings.jwt_secret == secret

    def test_jwt_secret_31_chars_raises_value_error(self):
        """A non-empty jwt_secret shorter than 32 chars must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            self._make_settings(jwt_secret="a" * 31)
        assert "JWT_SECRET" in str(exc_info.value)

    def test_jwt_secret_1_char_raises_value_error(self):
        """Single-character jwt_secret must raise ValidationError."""
        with pytest.raises(ValidationError):
            self._make_settings(jwt_secret="x")

    def test_jwt_secret_error_message_mentions_32_characters(self):
        """Error message must guide the user to the minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            self._make_settings(jwt_secret="tooshort")
        assert "32" in str(exc_info.value)

    # -----------------------------------------------------------------------
    # openai_api_key validation
    # -----------------------------------------------------------------------

    def test_openai_api_key_empty_string_is_allowed(self):
        """Empty openai_api_key is treated as 'not set' — no validation error."""
        settings = self._make_settings(openai_api_key="")
        assert settings.openai_api_key == ""

    def test_openai_api_key_exactly_8_chars_is_valid(self):
        """An 8-character key is the minimum valid length."""
        key = "sk-12345"
        settings = self._make_settings(openai_api_key=key)
        assert settings.openai_api_key == key

    def test_openai_api_key_longer_than_8_chars_is_valid(self):
        """Real OpenAI keys (50+ chars) must always pass."""
        key = "sk-" + "a" * 50
        settings = self._make_settings(openai_api_key=key)
        assert settings.openai_api_key == key

    def test_openai_api_key_7_chars_raises_value_error(self):
        """A non-empty key shorter than 8 chars must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            self._make_settings(openai_api_key="sk-ab")
        assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_openai_api_key_1_char_raises_value_error(self):
        """Single-character key must raise ValidationError."""
        with pytest.raises(ValidationError):
            self._make_settings(openai_api_key="x")

    def test_openai_api_key_error_message_says_invalid(self):
        """Error message must indicate the key looks invalid."""
        with pytest.raises(ValidationError) as exc_info:
            self._make_settings(openai_api_key="bad")
        assert "invalid" in str(exc_info.value).lower()

    # -----------------------------------------------------------------------
    # Both secrets invalid simultaneously
    # -----------------------------------------------------------------------

    def test_both_secrets_too_short_raises_validation_error(self):
        """When both secrets are set but too short, ValidationError is raised."""
        with pytest.raises(ValidationError):
            self._make_settings(jwt_secret="short", openai_api_key="x")

    # -----------------------------------------------------------------------
    # Valid combination (both set, both long enough)
    # -----------------------------------------------------------------------

    def test_both_secrets_valid_does_not_raise(self):
        """When both secrets meet minimum lengths, no error is raised."""
        settings = self._make_settings(
            jwt_secret="a" * 32,
            openai_api_key="sk-" + "b" * 20,
        )
        assert len(settings.jwt_secret) >= 32
        assert len(settings.openai_api_key) >= 8
