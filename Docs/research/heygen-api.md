# Research: HeyGen REST API

**Date researched:** 2026-03-09
**Library version:** REST API v2 (no Python SDK)
**Researched by:** Research Assistant Agent
**Status:** Current (rejected in ADR-005 — documented for reference)

---

## Question Being Answered

What are HeyGen's capabilities, costs, and privacy implications for avatar video generation, and why was it rejected for CR8 in favor of Kokoro TTS?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| HeyGen API Docs | https://docs.heygen.com/ | 2026-03-09 |
| Create Avatar Video V2 | https://docs.heygen.com/reference/create-an-avatar-video-v2 | 2026-03-09 |
| API Limits | https://docs.heygen.com/reference/limits | 2026-03-09 |
| Webhook Events | https://docs.heygen.com/docs/using-heygens-webhook-events | 2026-03-09 |
| HeyGen Privacy Policy | https://www.heygen.com/privacy | 2026-03-09 |
| HeyGen Trust Center | https://security.heygen.com/ | 2026-03-09 |
| HeyGen API Pricing | https://www.heygen.com/api-pricing | 2026-03-09 |
| HeyGen Status Page | https://status.heygen.com/ | 2026-03-09 |

## What We Found

### API Overview

```python
import requests

HEYGEN_API_KEY = "your-api-key"
BASE_URL = "https://api.heygen.com"

# Create an avatar video
response = requests.post(
    f"{BASE_URL}/v2/video/generate",
    headers={
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json",
    },
    json={
        "video_inputs": [{
            "character": {
                "type": "avatar",
                "avatar_id": "Daisy-inskirt-20220818",
                "avatar_style": "normal",
            },
            "voice": {
                "type": "text",
                "input_text": "Welcome to today's lecture...",
                "voice_id": "en-US-JennyNeural",
                "speed": 1.0,
            },
            "background": {
                "type": "color",
                "value": "#FFFFFF",
            },
        }],
        "dimension": {"width": 1920, "height": 1080},
    },
)
video_id = response.json()["data"]["video_id"]

# Poll for completion (5-30 minutes)
status = requests.get(
    f"{BASE_URL}/v2/video/status",
    params={"video_id": video_id},
    headers={"X-Api-Key": HEYGEN_API_KEY},
)
```

### Key API Methods / Concepts

| Endpoint | Purpose | Notes |
|----------|---------|-------|
| `POST /v2/video/generate` | Create standard avatar video | 5-30 min processing |
| `POST /v2/video/av4/generate` | Create Avatar IV video (advanced) | 6x credit cost |
| `GET /v2/video/status` | Poll video status | Returns `pending`, `processing`, `completed`, `failed` |
| `POST /v2/video/webhook` | Register webhook URL | HMAC-SHA256 signature verification |
| `GET /v2/avatars` | List available avatars | 30+ built-in avatars |
| `GET /v2/voices` | List available voices | 100+ voices, multiple languages |

### Pricing Model

| Item | Cost | Notes |
|------|------|-------|
| Standard avatar | 1 credit = 1 minute | $0.99/credit (Pro), $0.50/credit (Scale) |
| Avatar IV (advanced) | 1 credit = 10 seconds | ~6 credits/minute — 6x more expensive |
| **CR8 at scale** | ~$12,500/month | 1000 PDFs × 5 videos × ~2.5 min avg |

### Webhook Support

```python
# Webhook payload
{
    "event_type": "avatar_video.success",
    "event_data": {
        "video_id": "abc123",
        "url": "https://resource.heygen.com/video/abc123.mp4",
        "duration": 145.2,
    },
}
# Verify with HMAC-SHA256 signature in X-Heygen-Signature header
```

## Why ADR-005 Rejected HeyGen

| Concern | Detail |
|---------|--------|
| **Cost** | $12.5k+/month at scale vs. Kokoro's ~$10-50/month (GPU compute only) |
| **Data sovereignty** | Curriculum scripts transmitted to HeyGen servers; not deleted after processing |
| **Unnecessary features** | Avatar lip-sync not needed for slide narration (CR8 uses slide images + voiceover) |
| **Vendor lock-in** | Switching requires regenerating all videos; no export of avatar models |
| **Reliability** | ~49 outages/year; avg 86 min resolution time |

## When to Reconsider

HeyGen could work as an **optional premium tier (v0.6+)** if:
- User explicitly opts in with data consent
- Enterprise customers pay for their own HeyGen credits
- Professional avatar presentation is a product differentiator
- Implemented as a separate service behind a feature flag

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs | None | No Python SDK; REST API only |
| Compliance | SOC 2 Type 2, GDPR, CCPA | Enterprise-grade certifications |
| Data storage | AWS (US region) | Scripts stored on HeyGen infrastructure |
| License | Commercial API | Per-credit pricing; no open-source option |
| Known incidents | None published | Status page shows high availability |

**Verdict:** SAFE to integrate technically, but REJECTED for CR8 due to cost and data sovereignty concerns (ADR-005). Document for future reference only.

## Decision Made

Based on this research, we will:
> Not integrate HeyGen at this time, per ADR-005. Kokoro TTS + ffmpeg provides equivalent narrated video output at <1% of the cost with full data sovereignty. This research note is preserved for future reference if a premium avatar tier is considered in v0.6+.

## Files This Affects

- None currently — HeyGen is not integrated
- Future: `backend/services/heygen_client.py` (if premium tier is added)

---
*If this research is more than 6 months old or the library has had a major version bump, re-verify before implementing.*
