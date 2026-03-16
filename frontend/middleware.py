"""Security middleware and auth dependencies for CR8 frontend.

Provides:
- ``get_current_user`` — FastAPI dependency supporting dual auth
  (JWT Bearer header first, falls back to legacy session cookie).
- ``SecurityHeadersMiddleware`` — adds CSP, X-Frame-Options, etc.
- Rate-limiter helpers shared by auth routes.
"""

import logging
import re
import threading
import time

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from backend.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JOB_ID_RE = re.compile(r"^[a-f0-9]{8}$")
MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024
_PUBLIC_PATHS = frozenset({
    "/login", "/api/auth/login", "/api/auth/register",
    "/api/auth/refresh", "/api/auth/logout", "/health",
})

# ---------------------------------------------------------------------------
# Rate limiter (IP -> list of failed-attempt timestamps)
# ---------------------------------------------------------------------------

_failed_attempts: dict[str, list[float]] = {}
_failed_attempts_lock = threading.Lock()
MAX_ATTEMPTS = 5
LOCKOUT_WINDOW = 900.0  # 15-minute sliding window


def check_rate_limit(ip: str) -> bool:
    """Return True if this IP is still allowed to attempt login."""
    now = time.time()
    with _failed_attempts_lock:
        attempts = [t for t in _failed_attempts.get(ip, []) if now - t < LOCKOUT_WINDOW]
        _failed_attempts[ip] = attempts
        return len(attempts) < MAX_ATTEMPTS


def record_failed_attempt(ip: str) -> None:
    """Record a failed login attempt for rate-limiting."""
    now = time.time()
    with _failed_attempts_lock:
        attempts = [t for t in _failed_attempts.get(ip, []) if now - t < LOCKOUT_WINDOW]
        attempts.append(now)
        _failed_attempts[ip] = attempts


# ---------------------------------------------------------------------------
# Legacy session store (token -> expiry Unix timestamp)
# Kept for backward-compat with Jinja2 UI during transition to JWT.
# ---------------------------------------------------------------------------

_sessions: dict[str, float] = {}
_sessions_lock = threading.Lock()
SESSION_TTL = 8 * 3600  # 8 hours


def create_session() -> str:
    """Create a 256-bit cryptographically random session token."""
    import secrets

    token = secrets.token_hex(32)
    expiry = time.time() + SESSION_TTL
    with _sessions_lock:
        _sessions[token] = expiry
        now = time.time()
        for t in [k for k, exp in _sessions.items() if exp < now]:
            del _sessions[t]
    return token


def is_valid_session(token: str | None) -> bool:
    """Return True only if the token exists and has not expired."""
    if not token:
        return False
    with _sessions_lock:
        expiry = _sessions.get(token)
        if expiry is None:
            return False
        if time.time() > expiry:
            del _sessions[token]
            return False
        return True


def invalidate_session(token: str) -> None:
    """Remove a session token from the store."""
    with _sessions_lock:
        _sessions.pop(token, None)


# ---------------------------------------------------------------------------
# JWT + session dual-auth dependency
# ---------------------------------------------------------------------------

def _extract_bearer_token(request: Request) -> str | None:
    """Extract JWT from Authorization: Bearer header."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def get_current_user(request: Request) -> dict | None:
    """FastAPI dependency: authenticate via JWT Bearer or legacy session.

    Returns user payload dict on success, None if unauthenticated.
    JWT Bearer takes priority over session cookie.

    Args:
        request: The incoming FastAPI request.

    Returns:
        Dict with user info (sub, email, role) or None.
    """
    # 1. Try JWT Bearer token
    token = _extract_bearer_token(request)
    if token:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "access":
                return None
            return {
                "user_id": payload["sub"],
                "email": payload.get("email", ""),
                "role": payload.get("role", "user"),
            }
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    # 2. Fall back to legacy session cookie
    session_token = request.cookies.get("cr8_session")
    if is_valid_session(session_token):
        return {"user_id": "legacy-session", "email": "", "role": "user"}

    return None


# ---------------------------------------------------------------------------
# Auth enforcement middleware (outermost — runs before routing)
# ---------------------------------------------------------------------------

class AuthMiddleware:
    """Block requests that lack a valid JWT or session, except public paths.

    Pure ASGI implementation — avoids ``BaseHTTPMiddleware``'s response body
    buffering which corrupts ``Content-Length`` on ``FileResponse``.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """Check authentication for non-public paths."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = request.url.path

        # Public paths, static assets, and view routes pass through
        if (
            path in _PUBLIC_PATHS
            or path.startswith(("/static/", "/assets/", "/api/view/", "/api/download/"))
        ):
            await self.app(scope, receive, send)
            return

        user = await get_current_user(request)
        if user is not None:
            # Stash user info on request state for downstream routes
            scope.setdefault("state", {})
            scope["state"]["user"] = user
            await self.app(scope, receive, send)
            return

        # Not authenticated — send error response directly
        if path.startswith("/api/"):
            response = JSONResponse({"error": "Authentication required"}, status_code=401)
        else:
            response = RedirectResponse(url="/login", status_code=302)
        await response(scope, receive, send)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

_SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    # SAMEORIGIN allows our SPA to embed PDFs in iframes
    (b"x-frame-options", b"SAMEORIGIN"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"content-security-policy", (
        b"default-src 'self'; "
        b"script-src 'self' 'unsafe-inline'; "
        b"style-src 'self' 'unsafe-inline'; "
        b"img-src 'self' data:; "
        b"font-src 'self'; "
        b"media-src 'self'; "
        b"frame-src 'self'"
    )),
]


class SecurityHeadersMiddleware:
    """Add security headers to all responses.

    Pure ASGI implementation — avoids ``BaseHTTPMiddleware``'s response body
    buffering which corrupts ``Content-Length`` on ``FileResponse``.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """Intercept response start to inject security headers."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Buffer the start message so we can fix Content-Length if the
        # body turns out to be a different size (race with FileResponse
        # stat, or 204 responses with accidental body).
        state: dict = {"start_message": None}

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(_SECURITY_HEADERS)
                state["start_message"] = {**message, "headers": headers}
                return  # Don't send yet — wait for body

            if message["type"] == "http.response.body":
                start = state.get("start_message")
                if start is not None:
                    body = message.get("body", b"")
                    more_body = message.get("more_body", False)
                    # For single-chunk responses, fix Content-Length if
                    # it doesn't match the actual body length.
                    if not more_body:
                        _fix_content_length(start, len(body))
                    await send(start)
                    state["start_message"] = None
                await send(message)
                return

            await send(message)

        await self.app(scope, receive, send_with_headers)


def _fix_content_length(start_message: dict, body_len: int) -> None:
    """Correct the Content-Length header in *start_message* if it
    disagrees with *body_len*.

    Mutates the headers list in place.
    """
    headers = start_message.get("headers", [])
    for i, (name, value) in enumerate(headers):
        if name == b"content-length":
            try:
                declared = int(value)
            except (ValueError, TypeError):
                break
            if declared != body_len:
                logger.warning(
                    "Content-Length mismatch: declared=%d, actual=%d — correcting",
                    declared,
                    body_len,
                )
                headers[i] = (b"content-length", str(body_len).encode())
            break
