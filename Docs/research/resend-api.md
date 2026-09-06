# Research: Resend Transactional Email API

**Date researched:** 2026-09-06
**Library version:** REST API (no Python SDK used — direct `requests` calls)
**Researched by:** Cline agent
**Status:** Current

---

## Question Being Answered

How do we send password-reset emails from CR8 using Resend, without adding a
new dependency (the project already uses `requests`)?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| Send Email API reference | https://resend.com/docs/api-reference/emails/send-email | 2026-09-06 |
| Introduction / quickstart | https://resend.com/docs/introduction | 2026-09-06 |

## What We Found

### The Correct Approach

```python
import requests

resp = requests.post(
    "https://api.resend.com/emails",
    headers={
        "Authorization": "Bearer re_xxxxxxxxx",
        "Content-Type": "application/json",
    },
    json={
        "from": "Acme <onboarding@resend.dev>",
        "to": ["delivered@resend.dev"],
        "subject": "hello world",
        "text": "it works!",   # or "html": "<p>it works!</p>"
    },
    timeout=10,
)
resp.raise_for_status()
message_id = resp.json()["id"]  # e.g. "49a3999c-0ce1-4ea6-ab68-afcd6dc2e794"
```

### Key API Methods / Concepts

| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `POST /emails` | Send a single transactional email | Returns `200` with `{"id": "..."}` |
| `Authorization: Bearer re_…` | Auth header | API key has the `re_` prefix |
| `from` | Sender address | Must be a **verified domain** (or `onboarding@resend.dev` in test mode) |
| `to` | Recipient(s) | Accepts a string or a list of strings |
| `text` / `html` | Email body | At least one required |

### Configuration Required

```bash
RESEND_API_KEY=re_xxxxxxxxx
RESEND_FROM_EMAIL=CR8 <noreply@yourdomain.com>
```

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| `resend` Python SDK | Adds a new dependency; `requests` already covers the single endpoint we need |
| SMTP | Removed — Resend is the sole email provider (dev-log fallback only) |

## Known Gotchas / Edge Cases

- The `from` domain must be verified in Resend before production sending; use
  `onboarding@resend.dev` for development.
- `to` can be a string or list — we always send a single-element list.
- Non-2xx responses raise via `requests.raise_for_status()`; wrap in try/except
  so a failed email doesn't break the forgot-password flow (the token is still
  created, and delivery is retried by the user re-requesting).

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (critical/high) | None (REST API only) | No Python SDK to scan |
| License | Commercial API | Per-email pricing; not open-source |
| Data transmitted | `to`, `subject`, `text` | Minimal PII (recipient email + reset link) |
| Key handling | `RESEND_API_KEY` env var | Never logged; only sent as Bearer header |

**Verdict:** SAFE to add — no dependency, minimal data footprint.

## Decision Made

Based on this research, we will:
> Integrate Resend via a direct `requests.post` call in `backend/services/email_service.py`,
> as the sole email provider (with a dev-log fallback when unconfigured).

## Files This Affects

- `backend/services/email_service.py` — Resend provider + dev-log fallback
- `backend/config.py` — `resend_api_key`, `resend_from_email`
- `backend/tests/test_email_service.py` — provider-selection and failure-path tests

---

*If this research is more than 6 months old or the API has had a major version bump, re-verify before implementing.*
