# ADR-002: Dual-Auth Strategy (JWT + Legacy Session) During Frontend Migration

**Date:** 2026-03-09
**Status:** Accepted
**Deciders:** Shreyas Jagannath (engineering lead)

---

## Context

CR8 is migrating its frontend from a Jinja2 prototype (server-rendered HTML, session-cookie auth) to a React SPA (Vite + Tailwind, JWT auth). The migration spans v0.5.2 through v0.5.3 — during this window, both frontends must work simultaneously so the existing demo remains functional while React is built.

The legacy Jinja2 UI uses a single shared password (`AUTH_PASSWORD` env var) checked with bcrypt, issuing an opaque session token stored in process memory. This approach is unsuitable for a SPA: session cookies require same-origin requests, don't work with `Authorization: Bearer` headers, and provide no user identity (all sessions appear as the same anonymous user).

The React SPA needs stateless JWT auth with per-user accounts so that job history, quiz results, and chat sessions can be attributed to individual users. However, ripping out legacy auth before React is ready would break the demo for stakeholders.

## Decision

> We will use a dual-auth strategy — JWT Bearer tokens for the React SPA and legacy session cookies for the Jinja2 UI — coexisting until React fully replaces Jinja2 after v0.5.3.

**JWT configuration:**
- Algorithm: HS256 (symmetric, single-service deployment)
- Library: PyJWT + bcrypt
- Access token: 8 hours, returned in response body, sent via `Authorization: Bearer` header
- Refresh token: 7 days, stored in httpOnly cookie scoped to `/api/auth/refresh`
- Registration: open (no invite codes) — stakeholders self-serve during demos

**Legacy session configuration:**
- 256-bit random token via `secrets.token_hex(32)`
- 8-hour TTL, stored in process-memory dict with threading lock
- Single shared password checked against `AUTH_PASSWORD` env var

**Auth resolution order** (in `get_current_user()`):
1. Check `Authorization: Bearer` header for valid JWT access token
2. Fall back to `cr8_session` cookie for valid legacy session
3. Return `None` if neither is present

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Dual-auth JWT + legacy session (chosen)** | No breaking change during migration; React gets proper stateless auth from day one; clean deprecation path after v0.5.3 | Two auth code paths to maintain temporarily; in-memory session store doesn't scale horizontally; legacy users have no real identity |
| **JWT-only immediately** | Single auth path; simpler code; per-user identity everywhere | Breaks Jinja2 demo before React is ready; forces a hard cutover with no fallback |
| **Session-only (defer JWT)** | No new auth code needed yet | Session cookies don't work for SPAs (no Bearer header, CSRF issues); delays migration; would need JWT later anyway |
| **External OAuth provider (Auth0, Clerk)** | Battle-tested; social login; hosted dashboard | Vendor dependency and cost; added latency; overkill for current demo stage; complicates local dev |

## Consequences

**Positive:**
- Jinja2 demo keeps working throughout the React migration — no stakeholder downtime
- React SPA gets proper stateless auth from day one (no CSRF, works with `fetch`)
- Refresh token in httpOnly cookie prevents XSS-based token theft
- Per-user accounts enable job history, quiz tracking, and chat attribution
- Clean removal path: delete legacy session code after v0.5.3

**Negative / Trade-offs:**
- Two auth code paths to test until Jinja2 is removed (accepted as temporary)
- In-memory session store does not survive restarts or scale horizontally (acceptable: single Cloud Run instance during transition, sessions are ephemeral)
- Open registration means anyone with the URL can create an account (acceptable for demo phase; add invite codes or admin approval in v0.6 if needed)
- Legacy session users appear as `user_id: "legacy-session"` — their jobs won't link to real user accounts in the database

**Neutral:**
- `POST /api/auth/login` handles both modes: presence of `email` field triggers JWT mode, password-only triggers legacy mode
- Rate limiting (5 attempts / 15 min per IP) applies uniformly to both auth paths
- `SecurityHeadersMiddleware` and CORS settings apply regardless of auth method

## Implementation Notes

- **Files affected:**
  - `backend/services/auth_service.py` — JWT create/verify, bcrypt password hashing
  - `frontend/middleware.py` — `get_current_user()` dual-auth dependency, `AuthMiddleware`, session store, rate limiter
  - `frontend/auth_routes.py` — `/api/auth/*` endpoints (register, login, refresh, me, logout) + legacy login branch
  - `backend/config.py` — `jwt_secret`, `jwt_algorithm`, `jwt_access_expiry_minutes`, `jwt_refresh_expiry_days`, `allowed_origins`
- **Patterns to follow:**
  - Always check JWT Bearer first, session cookie second (never reverse the order)
  - Refresh token cookie must be scoped to `path="/api/auth/refresh"` — never send it on other requests
  - `verify_token()` enforces `type` claim to prevent access/refresh token confusion
  - `JWT_SECRET` must be at least 32 bytes in production (validated at startup)
- **Things to avoid:**
  - Do NOT store access tokens in cookies — they belong in `Authorization` header only
  - Do NOT add new features to legacy session auth — it is frozen and awaiting removal
  - Do NOT use `["*"]` for CORS origins — use the explicit `ALLOWED_ORIGINS` env var
- **Removal plan (post v0.5.3):**
  1. Delete `_sessions`, `create_session()`, `is_valid_session()`, `invalidate_session()` from `middleware.py`
  2. Remove legacy password-only branch from `auth_routes.py` login endpoint
  3. Remove `AUTH_PASSWORD` env var and `_PASSWORD_HASH` from `auth_routes.py`
  4. Remove `cr8_session` cookie fallback from `get_current_user()`
  5. Update `AuthMiddleware` to JWT-only

## References

- Auth service: `backend/services/auth_service.py`
- Middleware: `frontend/middleware.py`
- Auth routes: `frontend/auth_routes.py`
- Config: `backend/config.py` (JWT settings)
- DB schema: `backend/db/schema.sql` (users table with password_hash)
- Frontend CLAUDE.md: `frontend/CLAUDE.md` (authentication section)
