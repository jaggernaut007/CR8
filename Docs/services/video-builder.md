# Video Builder

**File**: `backend/services/video_builder.py`

Submits scripts to HeyGen API v2 for AI avatar video generation. Supports configurable avatar emotion, speech speed, and parallel generation.

## Usage

```python
from backend.services.video_builder import generate_video

video_path = generate_video(
    script="Your narration text...",
    output_path="outputs/video_01.mp4",
)
```

## Configuration

| Setting | Config Variable | Default | Description |
|---------|----------------|---------|-------------|
| Provider | `VIDEO_PROVIDER` | `heygen` | `heygen` or `synthesia` |
| Emotion | `VIDEO_AVATAR_EMOTION` | `Friendly` | Avatar facial expression |
| Speed | `VIDEO_AVATAR_SPEED` | `1.05` | Speech rate multiplier |
| Concurrency | `VIDEO_MAX_WORKERS` | `4` | Parallel video generation jobs |
| Topic limit | `VIDEO_TOPIC_LIMIT` | `5` | Max topics to generate videos for |

## Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HEYGEN_API_KEY` | For HeyGen | HeyGen API key |
| `HEYGEN_AVATAR_ID` | For HeyGen | HeyGen avatar ID |
| `HEYGEN_VOICE_ID` | For HeyGen | HeyGen voice ID |
| `SYNTHESIA_API_KEY` | For Synthesia | Synthesia API key (alternative provider) |
| `SYNTHESIA_AVATAR_ID` | For Synthesia | Synthesia avatar ID |

## Notes

- Video generation is optional and disabled by default in the web UI
- Selecting video output auto-enables Script + PPT generation
- Videos are generated in parallel using `ThreadPoolExecutor` with `VIDEO_MAX_WORKERS` threads
- Only the first `VIDEO_TOPIC_LIMIT` topics get videos (default 5) to manage API costs
- The builder polls the HeyGen API for completion status after submitting each job
