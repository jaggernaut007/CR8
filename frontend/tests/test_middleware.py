"""Tests for frontend/middleware.py.

Covers:
- SecurityHeadersMiddleware — all 4 headers present on routed responses
- AuthMiddleware — public paths, protected paths, API vs non-API redirection
- _extract_bearer_token() — with and without Bearer prefix
- get_current_user() — valid JWT, expired JWT, wrong token type, valid session,
  expired session, missing session
- Session CRUD — create_session(), is_valid_session(), invalidate_session()
- Rate limiter — check_rate_limit(), record_failed_attempt() within/outside window

Notes on middleware ordering:
  ``add_middleware`` uses last-in-first-out wrapping, so the execution order is:
  AuthMiddleware (outermost) -> SecurityHeadersMiddleware -> CORS -> route handlers.
  When AuthMiddleware short-circuits (401 JSON or 302 redirect) it bypasses
  SecurityHeadersMiddleware entirely. Security header tests therefore use public
  paths (``/health``, ``/login``) and authenticated routes where the full stack
  executes.
"""

import asyncio
import os
import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

# Ensure AUTH_PASSWORD is set before importing the app
os.environ.setdefault("AUTH_PASSWORD", "CR8-AI")
os.environ.setdefault("COOKIE_SECURE", "false")

from backend.config import settings
from backend.services import auth_service
from frontend.app import app
from frontend.middleware import (
    LOCKOUT_WINDOW,
    MAX_ATTEMPTS,
    SESSION_TTL,
    _extract_bearer_token,
    _failed_attempts,
    _sessions,
    check_rate_limit,
    create_session,
    get_current_user,
    invalidate_session,
    is_valid_session,
    record_failed_attempt,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(headers=None):
    """Build a minimal Starlette Request with the given headers dict."""
    raw_headers = [
        (k.lower().encode(), v.encode())
        for k, v in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/test",
        "query_string": b"",
        "headers": raw_headers,
        "http_version": "1.1",
    }
    return Request(scope)


def _make_cookie_request(cookie_value):
    """Build a minimal Starlette Request carrying a cr8_session cookie."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"cookie", f"cr8_session={cookie_value}".encode()),
        ],
        "http_version": "1.1",
    }
    return Request(scope)


def _run(coro):
    """Run an async coroutine in a fresh event loop (sync test helper)."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Fixtures
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
    """Unauthenticated TestClient."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def authed_client():
    """TestClient with a pre-seeded valid legacy session cookie."""
    c = TestClient(app, raise_server_exceptions=False)
    token = create_session()
    c.cookies.set("cr8_session", token)
    return c


@pytest.fixture
def sample_user():
    """Fake user dict matching db_client shape."""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "password_hash": auth_service.hash_password("password123"),
        "role": "user",
    }


@pytest.fixture
def valid_access_token(sample_user):
    """A real signed access token for sample_user."""
    return auth_service.create_access_token(
        sample_user["id"], sample_user["email"], "user"
    )


@pytest.fixture
def expired_access_token():
    """A JWT access token whose exp is in the past."""
    payload = {
        "sub": "some-user-id",
        "email": "exp@example.com",
        "role": "user",
        "type": "access",
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
def refresh_token(sample_user):
    """A real signed refresh token (type == 'refresh', not 'access')."""
    return auth_service.create_refresh_token(sample_user["id"])


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------


class TestSecurityHeadersMiddleware:
    """Security headers are added to all responses that pass through
    SecurityHeadersMiddleware (i.e. requests AuthMiddleware forwards via call_next).
    Public paths like /health and /login traverse the full middleware stack.
    """

    def test_x_content_type_options_present_on_health(self, client):
        resp = client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options_present_on_health(self, client):
        resp = client.get("/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_referrer_policy_present_on_health(self, client):
        resp = client.get("/health")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_content_security_policy_present_on_health(self, client):
        resp = client.get("/health")
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp

    def test_csp_restricts_scripts_on_login_page(self, client):
        """Login page is a public route — goes through SecurityHeadersMiddleware."""
        resp = client.get("/login")
        csp = resp.headers.get("content-security-policy", "")
        assert "script-src 'self'" in csp

    def test_security_headers_on_authenticated_index(self, authed_client):
        """Authenticated GET / traverses the full middleware stack."""
        resp = authed_client.get("/")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_all_four_headers_present_on_login_page(self, client):
        """All four security headers must appear on a normal public response."""
        resp = client.get("/login")
        assert "x-content-type-options" in resp.headers
        assert "x-frame-options" in resp.headers
        assert "referrer-policy" in resp.headers
        assert "content-security-policy" in resp.headers


# ---------------------------------------------------------------------------
# AuthMiddleware — public paths pass through
# ---------------------------------------------------------------------------


class TestAuthMiddlewarePublicPaths:

    def test_login_page_is_accessible_without_auth(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_health_is_accessible_without_auth(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_api_auth_login_does_not_redirect(self, client):
        """Wrong password returns 401 from route logic, not a 302 from middleware."""
        resp = client.post("/api/auth/login", json={"password": "wrong"}, follow_redirects=False)
        assert resp.status_code != 302

    def test_api_auth_register_does_not_redirect(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"email": "new@example.com", "password": "short"},
            follow_redirects=False,
        )
        assert resp.status_code != 302

    def test_api_auth_logout_does_not_require_auth(self, client):
        """Logout is a public path — unauthenticated requests must not be redirected."""
        resp = client.post("/api/auth/logout", follow_redirects=False)
        assert resp.status_code != 302


# ---------------------------------------------------------------------------
# AuthMiddleware — protected paths require auth
# ---------------------------------------------------------------------------


class TestAuthMiddlewareProtectedPaths:

    def test_index_without_auth_redirects_to_login(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 302

    def test_index_redirect_target_is_login(self, client):
        resp = client.get("/", follow_redirects=False)
        assert "/login" in resp.headers["location"]

    def test_api_upload_without_auth_returns_401_not_redirect(self, client):
        resp = client.post(
            "/api/upload",
            files={"file": ("f.pdf", b"%PDF-1.0", "application/pdf")},
        )
        assert resp.status_code == 401

    def test_api_upload_401_returns_json_error(self, client):
        resp = client.post(
            "/api/upload",
            files={"file": ("f.pdf", b"%PDF-1.0", "application/pdf")},
        )
        assert "error" in resp.json()

    def test_api_progress_without_auth_returns_401(self, client):
        resp = client.get("/api/progress/deadbeef")
        assert resp.status_code == 401

    def test_api_start_without_auth_returns_401(self, client):
        resp = client.post("/api/start", json={"job_id": "deadbeef"})
        assert resp.status_code == 401

    def test_api_download_without_auth_returns_401(self, client):
        resp = client.get("/api/download/deadbeef/pdf")
        assert resp.status_code == 401

    def test_authenticated_request_passes_through(self, authed_client):
        resp = authed_client.get("/")
        assert resp.status_code == 200

    def test_jwt_bearer_passes_auth_middleware(self, client, valid_access_token):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_access_token}"},
        )
        assert resp.status_code == 200

    def test_static_assets_pass_through_without_auth(self, client):
        """Paths under /static/ must bypass AuthMiddleware (no redirect)."""
        resp = client.get("/static/nonexistent.css", follow_redirects=False)
        assert resp.status_code != 302


# ---------------------------------------------------------------------------
# Extract bearer token
# ---------------------------------------------------------------------------


class TestExtractBearerToken:

    def test_returns_token_when_bearer_prefix_present(self):
        req = _make_request(headers={"authorization": "Bearer mytoken123"})
        assert _extract_bearer_token(req) == "mytoken123"

    def test_returns_none_when_no_authorization_header(self):
        req = _make_request()
        assert _extract_bearer_token(req) is None

    def test_returns_none_when_token_scheme_is_not_bearer(self):
        req = _make_request(headers={"authorization": "Token sometoken"})
        assert _extract_bearer_token(req) is None

    def test_returns_none_when_header_is_empty(self):
        req = _make_request(headers={"authorization": ""})
        assert _extract_bearer_token(req) is None

    def test_returns_none_for_basic_auth_scheme(self):
        req = _make_request(headers={"authorization": "Basic dXNlcjpwYXNz"})
        assert _extract_bearer_token(req) is None

    def test_strips_only_bearer_prefix(self):
        """Token value after 'Bearer ' must be returned verbatim."""
        req = _make_request(headers={"authorization": "Bearer abc.def.ghi"})
        assert _extract_bearer_token(req) == "abc.def.ghi"

    def test_case_sensitive_bearer_prefix(self):
        """'bearer' (lowercase) must not match — scheme is case-sensitive."""
        req = _make_request(headers={"authorization": "bearer mytoken"})
        assert _extract_bearer_token(req) is None


# ---------------------------------------------------------------------------
# get_current_user() — JWT branch
# ---------------------------------------------------------------------------


class TestGetCurrentUserJWT:

    def test_valid_access_token_returns_user_dict(self, valid_access_token, sample_user):
        req = _make_request(headers={"authorization": f"Bearer {valid_access_token}"})
        user = _run(get_current_user(req))
        assert user is not None
        assert user["user_id"] == sample_user["id"]

    def test_valid_access_token_returns_email(self, valid_access_token, sample_user):
        req = _make_request(headers={"authorization": f"Bearer {valid_access_token}"})
        user = _run(get_current_user(req))
        assert user["email"] == sample_user["email"]

    def test_valid_access_token_returns_role(self, valid_access_token):
        req = _make_request(headers={"authorization": f"Bearer {valid_access_token}"})
        user = _run(get_current_user(req))
        assert user["role"] == "user"

    def test_expired_access_token_returns_none(self, expired_access_token):
        req = _make_request(headers={"authorization": f"Bearer {expired_access_token}"})
        user = _run(get_current_user(req))
        assert user is None

    def test_wrong_token_type_returns_none(self, refresh_token):
        """A refresh token presented as Bearer must be rejected (type != 'access')."""
        req = _make_request(headers={"authorization": f"Bearer {refresh_token}"})
        user = _run(get_current_user(req))
        assert user is None

    def test_invalid_signature_returns_none(self):
        req = _make_request(headers={"authorization": "Bearer not.a.valid.jwt"})
        user = _run(get_current_user(req))
        assert user is None

    def test_malformed_token_returns_none(self):
        req = _make_request(headers={"authorization": "Bearer thisisnotajwt"})
        user = _run(get_current_user(req))
        assert user is None


# ---------------------------------------------------------------------------
# get_current_user() — session cookie branch
# ---------------------------------------------------------------------------


class TestGetCurrentUserSession:

    def test_valid_session_cookie_returns_user_dict(self):
        token = create_session()
        req = _make_cookie_request(token)
        user = _run(get_current_user(req))
        assert user is not None

    def test_valid_session_cookie_returns_legacy_user_id(self):
        token = create_session()
        req = _make_cookie_request(token)
        user = _run(get_current_user(req))
        assert user["user_id"] == "legacy-session"

    def test_expired_session_cookie_returns_none(self):
        token = "expiredtoken999"
        _sessions[token] = time.time() - 1  # already in the past
        req = _make_cookie_request(token)
        user = _run(get_current_user(req))
        assert user is None

    def test_missing_session_cookie_returns_none(self):
        req = _make_request()  # no cookie header at all
        user = _run(get_current_user(req))
        assert user is None

    def test_unknown_session_token_returns_none(self):
        req = _make_cookie_request("nosuchtoken")
        user = _run(get_current_user(req))
        assert user is None

    def test_jwt_bearer_takes_priority_over_session_cookie(
        self, valid_access_token, sample_user
    ):
        """When both JWT Bearer and session cookie are present, JWT wins."""
        token = create_session()
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [
                (b"authorization", f"Bearer {valid_access_token}".encode()),
                (b"cookie", f"cr8_session={token}".encode()),
            ],
            "http_version": "1.1",
        }
        req = Request(scope)
        user = _run(get_current_user(req))
        assert user["user_id"] == sample_user["id"]


# ---------------------------------------------------------------------------
# Session CRUD — create_session()
# ---------------------------------------------------------------------------


class TestCreateSession:

    def test_create_session_returns_string(self):
        token = create_session()
        assert isinstance(token, str)

    def test_create_session_returns_64_char_hex(self):
        token = create_session()
        assert len(token) == 64
        assert all(c in "0123456789abcdef" for c in token)

    def test_create_session_adds_to_store(self):
        token = create_session()
        assert token in _sessions

    def test_create_session_stores_future_expiry(self):
        now = time.time()
        token = create_session()
        assert _sessions[token] > now

    def test_create_session_expiry_is_approx_8_hours(self):
        token = create_session()
        expected = time.time() + SESSION_TTL
        assert abs(_sessions[token] - expected) < 5  # within 5 seconds

    def test_create_session_evicts_expired_tokens(self):
        stale = "a" * 64
        _sessions[stale] = time.time() - 1  # already expired
        create_session()
        assert stale not in _sessions

    def test_create_session_tokens_are_unique(self):
        t1 = create_session()
        t2 = create_session()
        assert t1 != t2


# ---------------------------------------------------------------------------
# Session CRUD — is_valid_session()
# ---------------------------------------------------------------------------


class TestIsValidSession:

    def test_returns_true_for_valid_token(self):
        token = create_session()
        assert is_valid_session(token) is True

    def test_returns_false_for_expired_token(self):
        token = "e" * 64
        _sessions[token] = time.time() - 1
        assert is_valid_session(token) is False

    def test_expired_token_is_removed_from_store(self):
        token = "f" * 64
        _sessions[token] = time.time() - 1
        is_valid_session(token)
        assert token not in _sessions

    def test_returns_false_for_unknown_token(self):
        assert is_valid_session("nosuchtoken") is False

    def test_returns_false_for_none(self):
        assert is_valid_session(None) is False

    def test_returns_false_for_empty_string(self):
        assert is_valid_session("") is False


# ---------------------------------------------------------------------------
# Session CRUD — invalidate_session()
# ---------------------------------------------------------------------------


class TestInvalidateSession:

    def test_removes_token_from_store(self):
        token = create_session()
        invalidate_session(token)
        assert token not in _sessions

    def test_token_is_no_longer_valid_after_invalidation(self):
        token = create_session()
        invalidate_session(token)
        assert is_valid_session(token) is False

    def test_invalidate_unknown_token_does_not_raise(self):
        invalidate_session("nosuchtoken")  # must not raise

    def test_invalidate_idempotent(self):
        token = create_session()
        invalidate_session(token)
        invalidate_session(token)  # second call must not raise


# ---------------------------------------------------------------------------
# Rate limiter — check_rate_limit()
# ---------------------------------------------------------------------------


class TestCheckRateLimit:

    def test_new_ip_is_allowed(self):
        assert check_rate_limit("1.2.3.4") is True

    def test_ip_with_fewer_than_max_attempts_is_allowed(self):
        ip = "10.0.0.1"
        for _ in range(MAX_ATTEMPTS - 1):
            record_failed_attempt(ip)
        assert check_rate_limit(ip) is True

    def test_ip_with_max_attempts_is_blocked(self):
        ip = "10.0.0.2"
        for _ in range(MAX_ATTEMPTS):
            record_failed_attempt(ip)
        assert check_rate_limit(ip) is False

    def test_expired_attempts_do_not_count(self):
        ip = "10.0.0.3"
        # Manually insert timestamps that are outside the window
        _failed_attempts[ip] = [time.time() - LOCKOUT_WINDOW - 1] * MAX_ATTEMPTS
        assert check_rate_limit(ip) is True

    def test_check_rate_limit_cleans_up_expired_attempts(self):
        ip = "10.0.0.4"
        _failed_attempts[ip] = [time.time() - LOCKOUT_WINDOW - 1] * MAX_ATTEMPTS
        check_rate_limit(ip)
        assert _failed_attempts.get(ip) == []

    def test_different_ips_tracked_independently(self):
        ip_a = "192.168.1.1"
        ip_b = "192.168.1.2"
        for _ in range(MAX_ATTEMPTS):
            record_failed_attempt(ip_a)
        assert check_rate_limit(ip_a) is False
        assert check_rate_limit(ip_b) is True


# ---------------------------------------------------------------------------
# Rate limiter — record_failed_attempt()
# ---------------------------------------------------------------------------


class TestRecordFailedAttempt:

    def test_records_attempt_for_new_ip(self):
        record_failed_attempt("5.5.5.5")
        assert len(_failed_attempts["5.5.5.5"]) == 1

    def test_appends_attempt_for_existing_ip(self):
        ip = "6.6.6.6"
        record_failed_attempt(ip)
        record_failed_attempt(ip)
        assert len(_failed_attempts[ip]) == 2

    def test_timestamps_are_recent(self):
        ip = "7.7.7.7"
        before = time.time()
        record_failed_attempt(ip)
        after = time.time()
        ts = _failed_attempts[ip][0]
        assert before <= ts <= after

    def test_expired_attempts_are_pruned_on_record(self):
        ip = "8.8.8.8"
        _failed_attempts[ip] = [time.time() - LOCKOUT_WINDOW - 1] * 3
        record_failed_attempt(ip)
        # Old stale records are pruned; only the new one should remain
        assert len(_failed_attempts[ip]) == 1

    def test_within_window_attempts_are_retained(self):
        ip = "9.9.9.9"
        record_failed_attempt(ip)
        record_failed_attempt(ip)
        record_failed_attempt(ip)
        assert len(_failed_attempts[ip]) == 3
