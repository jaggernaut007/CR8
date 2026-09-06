"""Authentication routes for CR8.

Provides JWT-based auth (register, login, refresh, me, logout) plus
legacy session-cookie login for the Jinja2 UI during the transition period.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, UTC

import bcrypt
import jwt
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from backend.config import settings
from backend.services import auth_service, db_client, email_service
from frontend.middleware import (
    SESSION_TTL,
    check_rate_limit,
    check_reset_rate_limit,
    create_session,
    get_current_user,
    invalidate_session,
    record_failed_attempt,
    record_reset_attempt,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Cookie flags
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"

# Legacy single-password auth (kept for Jinja2 UI backward-compat)
_AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD", "CR8-AI")
_PASSWORD_HASH: bytes = bcrypt.hashpw(_AUTH_PASSWORD.encode(), bcrypt.gensalt())

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


# ---------------------------------------------------------------------------
# JWT auth routes
# ---------------------------------------------------------------------------


@router.post("/register", status_code=201)
async def register(request: Request, body: dict):
    """Register a new user account.

    Args:
        request: FastAPI request (used for DB pool access).
        body: JSON body with ``email`` and ``password``.

    Returns:
        201 with user_id and access token, or 400/409 on error.
    """
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip):
        return JSONResponse(
            {"error": "Too many failed attempts. Try again in 15 minutes."},
            status_code=429,
        )

    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        record_failed_attempt(ip)
        return JSONResponse(
            {"error": "Email and password are required"}, status_code=400
        )
    min_password_length = 6
    if len(password) < min_password_length:
        record_failed_attempt(ip)
        return JSONResponse(
            {"error": "Password must be at least 6 characters"}, status_code=400
        )

    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        return JSONResponse(
            {"error": "Database not available"}, status_code=503
        )

    # Check for existing user
    existing = await db_client.get_user_by_email(pool, email)
    if existing:
        record_failed_attempt(ip)
        return JSONResponse(
            {"error": "An account with this email already exists"}, status_code=409
        )

    password_hash = auth_service.hash_password(password)
    user = await db_client.create_user(pool, email, password_hash)

    access_token = auth_service.create_access_token(
        str(user["id"]), email, user.get("role", "user")
    )
    refresh_token = auth_service.create_refresh_token(str(user["id"]))

    response = JSONResponse(
        {
            "user_id": str(user["id"]),
            "access_token": access_token,
            "expires_in": settings.jwt_access_expiry_minutes * 60,
        },
        status_code=201,
    )
    response.set_cookie(
        key="cr8_refresh",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=settings.jwt_refresh_expiry_days * 86400,
        path="/api/auth/refresh",
    )
    logger.info("User registered: email=%s", email)
    return response


@router.post("/login")
async def login(request: Request, body: dict):
    """Authenticate and issue tokens.

    Supports two modes:
    1. JWT mode (email + password) — returns access_token, sets refresh cookie.
    2. Legacy mode (password only) — sets session cookie for Jinja2 UI.

    Args:
        request: FastAPI request.
        body: JSON body with ``password`` and optionally ``email``.

    Returns:
        200 with token/status, 401 on wrong credentials, 429 on rate limit.
    """
    ip = request.client.host if request.client else "unknown"

    if not check_rate_limit(ip):
        return JSONResponse(
            {"error": "Too many failed attempts. Try again in 15 minutes."},
            status_code=429,
        )

    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    # JWT mode: email + password against DB
    if email:
        pool = getattr(request.app.state, "db_pool", None)
        if pool is None:
            return JSONResponse(
                {"error": "Database not available"}, status_code=503
            )

        user = await db_client.get_user_by_email(pool, email)
        if not user or not auth_service.verify_password(
            password, user["password_hash"]
        ):
            record_failed_attempt(ip)
            logger.warning("Failed JWT login attempt from %s for email=%s", ip, email)
            return JSONResponse(
                {"error": "Invalid email or password"}, status_code=401
            )

        access_token = auth_service.create_access_token(
            str(user["id"]), email, user.get("role", "user")
        )
        refresh_token = auth_service.create_refresh_token(str(user["id"]))

        response = JSONResponse({
            "access_token": access_token,
            "expires_in": settings.jwt_access_expiry_minutes * 60,
        })
        response.set_cookie(
            key="cr8_refresh",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            secure=COOKIE_SECURE,
            max_age=settings.jwt_refresh_expiry_days * 86400,
            path="/api/auth/refresh",
        )
        logger.info("JWT login: email=%s", email)
        return response

    # Legacy mode: password-only against env var
    if not password or not bcrypt.checkpw(password.encode(), _PASSWORD_HASH):
        record_failed_attempt(ip)
        logger.warning("Failed legacy login attempt from %s", ip)
        return JSONResponse(
            {"error": "Incorrect password. Please try again."}, status_code=401
        )

    token = create_session()
    response = JSONResponse({"status": "ok"})
    response.set_cookie(
        key="cr8_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=SESSION_TTL,
    )
    logger.info("Legacy session login from %s", ip)
    return response


def _refresh_error_response(message: str) -> JSONResponse:
    """Build a 401 response that also clears the stale refresh cookie."""
    response = JSONResponse({"error": message}, status_code=401)
    response.delete_cookie("cr8_refresh", path="/api/auth/refresh")
    return response


@router.post("/refresh")
async def refresh(request: Request):
    """Issue a new access token using a valid refresh token cookie.

    Args:
        request: FastAPI request (reads ``cr8_refresh`` cookie).

    Returns:
        200 with new access_token, or 401 on invalid/missing refresh token.
    """
    refresh_token = request.cookies.get("cr8_refresh")
    if not refresh_token:
        return JSONResponse({"error": "No refresh token"}, status_code=401)

    try:
        payload = auth_service.verify_token(refresh_token, expected_type="refresh")
    except jwt.ExpiredSignatureError:
        logger.warning("Refresh token expired — user must re-login")
        return _refresh_error_response("Refresh token expired")
    except jwt.InvalidSignatureError:
        logger.warning(
            "Refresh token signature mismatch — likely JWT_SECRET "
            "changed after redeployment. User must re-login."
        )
        return _refresh_error_response("Invalid refresh token")
    except Exception:
        logger.exception("Refresh token verification failed")
        return _refresh_error_response("Invalid refresh token")

    user_id = payload["sub"]
    pool = getattr(request.app.state, "db_pool", None)

    # Re-fetch user to get current email/role
    email = ""
    role = "user"
    if pool:
        user = await db_client.get_user_by_id(pool, user_id)
        if user:
            email = user.get("email", "")
            role = user.get("role", "user")

    access_token = auth_service.create_access_token(user_id, email, role)
    logger.info("Token refreshed for user_id=%s", user_id)
    return {
        "access_token": access_token,
        "expires_in": settings.jwt_access_expiry_minutes * 60,
    }


@router.get("/me")
async def me(request: Request):
    """Return the current authenticated user's info.

    Args:
        request: FastAPI request (user set by auth middleware).

    Returns:
        200 with user info, or 401 if not authenticated.
    """
    user = await get_current_user(request)
    if user is None:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    return user


@router.post("/logout", status_code=204)
async def logout(request: Request):
    """Invalidate the current session and clear cookies.

    Args:
        request: FastAPI request.

    Returns:
        204 No Content on success.
    """
    # Clear legacy session
    session_token = request.cookies.get("cr8_session")
    if session_token:
        invalidate_session(session_token)

    response = Response(status_code=204)
    response.delete_cookie("cr8_session")
    response.delete_cookie("cr8_refresh", path="/api/auth/refresh")
    logger.info("User logged out")
    return response


@router.post("/forgot-password", status_code=202)
async def forgot_password(request: Request, body: dict):
    """Start a password reset by emailing a one-time link.

    Always returns the same 202 response whether or not the email exists, to
    avoid leaking which accounts are registered.

    Args:
        request: FastAPI request (used for DB pool access).
        body: JSON body with ``email``.

    Returns:
        202 with a generic message, 400 if email missing, 429 if rate-limited,
        503 if no database is available.
    """
    ip = request.client.host if request.client else "unknown"
    if not check_reset_rate_limit(ip):
        return JSONResponse(
            {"error": "Too many requests. Try again in 15 minutes."}, status_code=429
        )
    record_reset_attempt(ip)

    email = (body.get("email") or "").strip().lower()
    if not email:
        return JSONResponse({"error": "Email is required"}, status_code=400)

    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        return JSONResponse(
            {"error": "Database not available"}, status_code=503
        )

    user = await db_client.get_user_by_email(pool, email)
    if user is None:
        logger.info("Password reset requested for unknown email (no-op)")
        return JSONResponse(
            {"message": "If that email exists, a reset link has been sent."},
            status_code=202,
        )

    token = auth_service.generate_password_reset_token()
    token_hash = auth_service.hash_password_reset_token(token)
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.password_reset_token_ttl_minutes
    )

    await db_client.upsert_password_reset_token(
        pool, str(user["id"]), token_hash, expires_at
    )

    reset_link = (
        f"{settings.password_reset_base_url.rstrip('/')}/reset-password?token={token}"
    )
    sent = await asyncio.to_thread(
        email_service.send_password_reset_email, email, reset_link
    )
    if not sent:
        logger.warning("Password reset email delivery failed for user_id=%s", user["id"])

    logger.info("Password reset link generated for user_id=%s", user["id"])
    return JSONResponse(
        {"message": "If that email exists, a reset link has been sent."},
        status_code=202,
    )


@router.post("/reset-password")
async def reset_password(request: Request, body: dict):
    """Reset a password using a valid one-time reset token.

    Args:
        request: FastAPI request (used for DB pool access).
        body: JSON body with ``token`` and ``password``.

    Returns:
        200 on success, 400 on missing/invalid/expired token or short password,
        429 if rate-limited, 503 if no database is available.
    """
    ip = request.client.host if request.client else "unknown"
    if not check_reset_rate_limit(ip):
        return JSONResponse(
            {"error": "Too many requests. Try again in 15 minutes."}, status_code=429
        )
    record_reset_attempt(ip)

    token = (body.get("token") or "").strip()
    password = body.get("password") or ""
    min_password_length = 6
    if not token or not password:
        return JSONResponse(
            {"error": "Token and new password are required"}, status_code=400
        )
    if len(password) < min_password_length:
        return JSONResponse(
            {"error": "Password must be at least 6 characters"}, status_code=400
        )

    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        return JSONResponse(
            {"error": "Database not available"}, status_code=503
        )

    token_hash = auth_service.hash_password_reset_token(token)
    record = await db_client.get_password_reset_token_by_hash(pool, token_hash)

    token_valid = record is not None and record["expires_at"] >= datetime.now(UTC)
    if not token_valid:
        if record is not None:
            await db_client.delete_password_reset_tokens(pool, record["user_id"])
        return JSONResponse(
            {"error": "Invalid or expired reset token"}, status_code=400
        )

    password_hash = auth_service.hash_password(password)
    await db_client.update_user_password(pool, record["user_id"], password_hash)
    await db_client.delete_password_reset_tokens(pool, record["user_id"])

    logger.info("Password reset completed for user_id=%s", record["user_id"])
    return JSONResponse(
        {"message": "Password has been reset. You can now sign in."},
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Jinja2 login page (serves HTML, not API)
# ---------------------------------------------------------------------------


@router.get("/login-page", response_class=HTMLResponse, include_in_schema=False)
async def login_page():
    """Serve the login HTML page (legacy Jinja2 UI)."""
    html_path = os.path.join(TEMPLATE_DIR, "login.html")
    with open(html_path) as f:
        return HTMLResponse(content=f.read())
