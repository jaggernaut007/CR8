"""Tests for frontend/auth_routes.py and frontend/middleware.py get_current_user.

Covers:
- POST /api/auth/register — happy path, duplicate email, short password, no DB
- POST /api/auth/login (JWT mode) — happy path, wrong password, no DB
- POST /api/auth/refresh — happy path, missing cookie, invalid token
- GET  /api/auth/me — JWT Bearer, legacy session, unauthenticated
- POST /api/auth/logout — 204 response, cookie clearing
- get_current_user — JWT Bearer, legacy session cookie, no auth

Notes on /api/auth/refresh and /api/auth/logout:
Both routes sit behind AuthMiddleware. They require a valid JWT Bearer or session
cookie to pass the middleware check. The refresh and logout endpoints are therefore
tested using ``authed_client`` (pre-seeded session) to satisfy AuthMiddleware, then
the route-level logic is exercised via the cr8_refresh cookie or session state.
"""

import os
import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Set auth env before importing the app so _PASSWORD_HASH is computed
os.environ.setdefault("AUTH_PASSWORD", "CR8-AI")
os.environ.setdefault("COOKIE_SECURE", "false")

from backend.services import auth_service
from frontend.app import app
from frontend.middleware import _failed_attempts, _sessions, create_session


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_auth_state():
    """Clear rate-limit and session state before and after each test."""
    _sessions.clear()
    _failed_attempts.clear()
    yield
    _sessions.clear()
    _failed_attempts.clear()


@pytest.fixture
def client():
    """Unauthenticated TestClient — no session or JWT cookie pre-set."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def authed_client():
    """TestClient with a valid legacy session cookie pre-seeded."""
    c = TestClient(app, raise_server_exceptions=False)
    token = create_session()
    c.cookies.set("cr8_session", token)
    return c


@pytest.fixture
def sample_user():
    """A fake user dict as returned by db_client functions."""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "password_hash": auth_service.hash_password("password123"),
        "role": "user",
    }


@pytest.fixture
def mock_db_pool(app=app):
    """Attach a sentinel object as app.state.db_pool, yield, then remove it."""
    sentinel = object()
    app.state.db_pool = sentinel
    yield sentinel
    del app.state.db_pool


@pytest.fixture
def valid_access_token(sample_user):
    """A real signed access token for sample_user."""
    return auth_service.create_access_token(
        sample_user["id"], sample_user["email"], "user"
    )


@pytest.fixture
def valid_refresh_token(sample_user):
    """A real signed refresh token for sample_user."""
    return auth_service.create_refresh_token(sample_user["id"])


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------


class TestRegister:

    def test_register_returns_201(self, client, mock_db_pool, sample_user):
        with (
            patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get,
            patch("frontend.auth_routes.db_client.create_user", new_callable=AsyncMock) as mock_create,
        ):
            mock_get.return_value = None
            mock_create.return_value = sample_user
            resp = client.post(
                "/api/auth/register",
                json={"email": "new@example.com", "password": "securepass"},
            )
        assert resp.status_code == 201

    def test_register_returns_user_id(self, client, mock_db_pool, sample_user):
        with (
            patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get,
            patch("frontend.auth_routes.db_client.create_user", new_callable=AsyncMock) as mock_create,
        ):
            mock_get.return_value = None
            mock_create.return_value = sample_user
            resp = client.post(
                "/api/auth/register",
                json={"email": "new@example.com", "password": "securepass"},
            )
        assert "user_id" in resp.json()

    def test_register_returns_access_token(self, client, mock_db_pool, sample_user):
        with (
            patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get,
            patch("frontend.auth_routes.db_client.create_user", new_callable=AsyncMock) as mock_create,
        ):
            mock_get.return_value = None
            mock_create.return_value = sample_user
            resp = client.post(
                "/api/auth/register",
                json={"email": "new@example.com", "password": "securepass"},
            )
        assert "access_token" in resp.json()

    def test_register_sets_refresh_cookie(self, client, mock_db_pool, sample_user):
        with (
            patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get,
            patch("frontend.auth_routes.db_client.create_user", new_callable=AsyncMock) as mock_create,
        ):
            mock_get.return_value = None
            mock_create.return_value = sample_user
            resp = client.post(
                "/api/auth/register",
                json={"email": "new@example.com", "password": "securepass"},
            )
        assert "cr8_refresh" in resp.cookies

    def test_register_duplicate_email_returns_409(self, client, mock_db_pool, sample_user):
        with patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_user
            resp = client.post(
                "/api/auth/register",
                json={"email": "existing@example.com", "password": "securepass"},
            )
        assert resp.status_code == 409

    def test_register_duplicate_email_error_message(self, client, mock_db_pool, sample_user):
        with patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_user
            resp = client.post(
                "/api/auth/register",
                json={"email": "existing@example.com", "password": "securepass"},
            )
        assert "already exists" in resp.json()["error"]

    def test_register_short_password_returns_400(self, client, mock_db_pool):
        resp = client.post(
            "/api/auth/register",
            json={"email": "new@example.com", "password": "abc"},
        )
        assert resp.status_code == 400

    def test_register_short_password_error_message(self, client, mock_db_pool):
        resp = client.post(
            "/api/auth/register",
            json={"email": "new@example.com", "password": "abc"},
        )
        assert "6 characters" in resp.json()["error"]

    def test_register_missing_email_returns_400(self, client, mock_db_pool):
        resp = client.post(
            "/api/auth/register",
            json={"password": "securepass"},
        )
        assert resp.status_code == 400

    def test_register_missing_password_returns_400(self, client, mock_db_pool):
        resp = client.post(
            "/api/auth/register",
            json={"email": "new@example.com"},
        )
        assert resp.status_code == 400

    def test_register_no_db_returns_503(self, client):
        # No mock_db_pool fixture — db_pool not set on app.state
        if hasattr(app.state, "db_pool"):
            del app.state.db_pool
        resp = client.post(
            "/api/auth/register",
            json={"email": "new@example.com", "password": "securepass"},
        )
        assert resp.status_code == 503

    def test_register_normalises_email_to_lowercase(self, client, mock_db_pool, sample_user):
        captured_emails = []

        async def capture_get(pool, email):
            captured_emails.append(email)

        with (
            patch("frontend.auth_routes.db_client.get_user_by_email", side_effect=capture_get),
            patch("frontend.auth_routes.db_client.create_user", new_callable=AsyncMock) as mock_create,
        ):
            mock_create.return_value = sample_user
            client.post(
                "/api/auth/register",
                json={"email": "UPPER@Example.COM", "password": "securepass"},
            )
        assert captured_emails[0] == "upper@example.com"


# ---------------------------------------------------------------------------
# POST /api/auth/login (JWT mode — email + password)
# ---------------------------------------------------------------------------


class TestLoginJWT:

    def test_jwt_login_returns_200(self, client, mock_db_pool, sample_user):
        with patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_user
            resp = client.post(
                "/api/auth/login",
                json={"email": sample_user["email"], "password": "password123"},
            )
        assert resp.status_code == 200

    def test_jwt_login_returns_access_token(self, client, mock_db_pool, sample_user):
        with patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_user
            resp = client.post(
                "/api/auth/login",
                json={"email": sample_user["email"], "password": "password123"},
            )
        assert "access_token" in resp.json()

    def test_jwt_login_sets_refresh_cookie(self, client, mock_db_pool, sample_user):
        with patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_user
            resp = client.post(
                "/api/auth/login",
                json={"email": sample_user["email"], "password": "password123"},
            )
        assert "cr8_refresh" in resp.cookies

    def test_jwt_login_wrong_password_returns_401(self, client, mock_db_pool, sample_user):
        with patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_user
            resp = client.post(
                "/api/auth/login",
                json={"email": sample_user["email"], "password": "wrongpassword"},
            )
        assert resp.status_code == 401

    def test_jwt_login_unknown_email_returns_401(self, client, mock_db_pool):
        with patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            resp = client.post(
                "/api/auth/login",
                json={"email": "nobody@example.com", "password": "password123"},
            )
        assert resp.status_code == 401

    def test_jwt_login_no_db_returns_503(self, client):
        if hasattr(app.state, "db_pool"):
            del app.state.db_pool
        resp = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert resp.status_code == 503

    def test_jwt_login_rate_limited_after_5_failures(self, client, mock_db_pool):
        with patch("frontend.auth_routes.db_client.get_user_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            for _ in range(5):
                client.post(
                    "/api/auth/login",
                    json={"email": "test@example.com", "password": "bad"},
                )
            resp = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "bad"},
            )
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# POST /api/auth/login (legacy mode — password only, no email)
# ---------------------------------------------------------------------------


class TestLoginLegacy:

    def test_legacy_login_correct_password_returns_200(self, client):
        resp = client.post("/api/auth/login", json={"password": "CR8-AI"})
        assert resp.status_code == 200

    def test_legacy_login_sets_session_cookie(self, client):
        resp = client.post("/api/auth/login", json={"password": "CR8-AI"})
        assert "cr8_session" in resp.cookies

    def test_legacy_login_wrong_password_returns_401(self, client):
        resp = client.post("/api/auth/login", json={"password": "wrong"})
        assert resp.status_code == 401

    def test_legacy_login_missing_password_returns_401(self, client):
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/auth/refresh
#
# /api/auth/refresh is protected by AuthMiddleware. Tests that exercise the
# happy path must pass the middleware first (authed_client provides a valid
# session cookie). Error-path tests that send no session still get 401 — the
# middleware 401 and the route 401 are indistinguishable from a client's view.
# ---------------------------------------------------------------------------


class TestRefresh:

    def test_refresh_returns_200(self, authed_client, mock_db_pool, sample_user, valid_refresh_token):
        with patch("frontend.auth_routes.db_client.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_user
            authed_client.cookies.set("cr8_refresh", valid_refresh_token)
            resp = authed_client.post("/api/auth/refresh")
        assert resp.status_code == 200

    def test_refresh_returns_new_access_token(self, authed_client, mock_db_pool, sample_user, valid_refresh_token):
        with patch("frontend.auth_routes.db_client.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_user
            authed_client.cookies.set("cr8_refresh", valid_refresh_token)
            resp = authed_client.post("/api/auth/refresh")
        assert "access_token" in resp.json()

    def test_refresh_no_auth_returns_401(self, client):
        """Unauthenticated request is blocked by AuthMiddleware with 401."""
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_invalid_refresh_token_returns_401(self, authed_client):
        """Valid session passes middleware; invalid cr8_refresh cookie causes route 401."""
        authed_client.cookies.set("cr8_refresh", "not.a.valid.token")
        resp = authed_client.post("/api/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_access_token_as_refresh_returns_401(self, authed_client, valid_access_token):
        """Passing an access token where a refresh token is expected should fail."""
        authed_client.cookies.set("cr8_refresh", valid_access_token)
        resp = authed_client.post("/api/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_works_without_db_pool(self, authed_client, sample_user, valid_refresh_token):
        """If no DB pool is configured, refresh still issues a token (empty email/role)."""
        if hasattr(app.state, "db_pool"):
            del app.state.db_pool
        authed_client.cookies.set("cr8_refresh", valid_refresh_token)
        resp = authed_client.post("/api/auth/refresh")
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_missing_refresh_cookie_returns_401(self, authed_client):
        """Session passes middleware but no cr8_refresh cookie — route returns 401."""
        resp = authed_client.post("/api/auth/refresh")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------


class TestMe:

    def test_me_with_valid_jwt_returns_200(self, client, valid_access_token):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_access_token}"},
        )
        assert resp.status_code == 200

    def test_me_with_valid_jwt_returns_user_id(self, client, sample_user, valid_access_token):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_access_token}"},
        )
        assert resp.json()["user_id"] == sample_user["id"]

    def test_me_with_valid_jwt_returns_email(self, client, sample_user, valid_access_token):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_access_token}"},
        )
        assert resp.json()["email"] == sample_user["email"]

    def test_me_with_valid_jwt_returns_role(self, client, valid_access_token):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_access_token}"},
        )
        assert resp.json()["role"] == "user"

    def test_me_with_legacy_session_returns_200(self, authed_client):
        resp = authed_client.get("/api/auth/me")
        assert resp.status_code == 200

    def test_me_with_legacy_session_returns_legacy_user_id(self, authed_client):
        resp = authed_client.get("/api/auth/me")
        assert resp.json()["user_id"] == "legacy-session"

    def test_me_unauthenticated_returns_401(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token_returns_401(self, client):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_me_refresh_token_in_bearer_returns_401(self, client, valid_refresh_token):
        """Supplying a refresh token in the Bearer header must be rejected."""
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_refresh_token}"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/auth/logout
#
# Logout is behind AuthMiddleware — unauthenticated requests get 401, not 204.
# ---------------------------------------------------------------------------


class TestLogout:

    def test_logout_returns_204(self, authed_client):
        resp = authed_client.post("/api/auth/logout")
        assert resp.status_code == 204

    def test_logout_deletes_session_cookie(self, authed_client):
        authed_client.post("/api/auth/logout")
        resp = authed_client.get("/", follow_redirects=False)
        assert resp.status_code == 302

    def test_logout_unauthenticated_returns_204(self, client):
        """Unauthenticated logout is allowed (idempotent, public path)."""
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 204

    def test_logout_invalidates_session_store(self, authed_client):
        """After logout the session token should no longer be valid."""
        # The authed_client session is in _sessions before logout
        sessions_before = len(_sessions)
        authed_client.post("/api/auth/logout")
        # After logout the session store should shrink by 1
        assert len(_sessions) == sessions_before - 1


# ---------------------------------------------------------------------------
# get_current_user (middleware unit tests exercised via /api/auth/me)
# ---------------------------------------------------------------------------


class TestGetCurrentUser:

    def test_bearer_token_returns_user_dict(self, client, sample_user, valid_access_token):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_access_token}"},
        )
        data = resp.json()
        assert data["user_id"] == sample_user["id"]
        assert data["email"] == sample_user["email"]

    def test_expired_bearer_token_returns_401(self, client):
        """A token with exp in the past must be rejected."""
        import jwt as pyjwt
        from datetime import UTC, datetime, timedelta

        from backend.config import settings

        payload = {
            "sub": "some-user-id",
            "email": "exp@example.com",
            "role": "user",
            "type": "access",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
        }
        expired_token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    def test_legacy_session_cookie_returns_user_dict(self, authed_client):
        resp = authed_client.get("/api/auth/me")
        assert resp.json()["user_id"] == "legacy-session"

    def test_expired_session_cookie_returns_401(self, client):
        """A session token whose expiry has passed must not authenticate."""
        token = "expiredtoken123"
        _sessions[token] = time.time() - 1  # already expired
        client.cookies.set("cr8_session", token)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_no_auth_returns_401_on_protected_route(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_malformed_bearer_header_returns_401(self, client):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "Token notbearer"},
        )
        assert resp.status_code == 401
