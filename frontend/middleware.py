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
from starlette.middleware.base import BaseHTTPMiddleware

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

class AuthMiddleware(BaseHTTPMiddleware):
    """Block requests that lack a valid JWT or session, except public paths."""

    async def dispatch(self, request: Request, call_next):
        """Check authentication for non-public paths."""
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # Allow static assets (SPA JS/CSS/images) and view routes
        # (view routes use the unguessable short_id as a capability token;
        # iframes, <video>, and <img> tags can't send Bearer headers)
        if request.url.path.startswith(("/static/", "/assets/", "/api/view/")):
            return await call_next(request)

        user = await get_current_user(request)
        if user is not None:
            # Stash user info on request state for downstream routes
            request.state.user = user
            return await call_next(request)

        # Not authenticated
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": "Authentication required"}, status_code=401)
        return RedirectResponse(url="/login", status_code=302)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        """Add security headers to the response."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        # SAMEORIGIN allows our SPA to embed PDFs in iframes
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "media-src 'self'; "
            "frame-src 'self'"
        )
        return response
