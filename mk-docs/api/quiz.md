# Quiz API Reference

All quiz endpoints require JWT authentication. Requests without a valid Bearer token receive HTTP 401.

## Endpoints

### POST `/api/quiz/generate`

Generate a quiz from a completed pipeline job.

**Request body:**

```json
{
  "job_id": "uuid-string",
  "question_count": 20
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `job_id` | `string` | Yes | — | Non-empty, must reference a completed job owned by the user |
| `question_count` | `integer` | No | 20 | 5-50 |

**Response (201):**

```json
{
  "quiz_id": "uuid-string",
  "question_count": 20
}
```

**Error responses:**

| Status | Reason |
|--------|--------|
| 401 | Authentication required |
| 400 | Job not complete / no topic data |
| 404 | Job not found or not owned by user |
| 422 | Invalid request body |
| 503 | Database unavailable |

---

### GET `/api/quiz/{quiz_id}`

Fetch a quiz with its questions. Answer fields are hidden until the user completes an attempt.

**Response (200):**

```json
{
  "quiz_id": "uuid-string",
  "title": "Quiz: lecture.pdf",
  "questions": [
    {
      "id": "uuid-string",
      "question_text": "What is...",
      "options": ["A", "B", "C", "D"],
      "difficulty": "medium"
    }
  ],
  "existing_attempt": null
}
```

!!! note "Answer hiding"
    Before the user submits an attempt, `correct_index`, `feedback_correct`, and `feedback_incorrect` are stripped from each question. After submission, the full data is returned.

---

### POST `/api/quiz/{quiz_id}/submit`

Submit quiz answers and receive scored results. Each quiz allows exactly one submission per user.

**Request body:**

```json
{
  "responses": [
    {
      "question_id": "uuid-string",
      "selected_index": 1,
      "time_spent_seconds": 30
    }
  ]
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `question_id` | `string` | Must match a question in the quiz |
| `selected_index` | `integer` | 0-3 |
| `time_spent_seconds` | `integer` | >= 0, default 0 |

**Response (200):**

```json
{
  "attempt_id": "uuid-string",
  "score": 85.0,
  "total": 20,
  "results": [
    {
      "question_id": "uuid-string",
      "selected_index": 1,
      "correct_index": 1,
      "is_correct": true,
      "feedback": "Correct! ..."
    }
  ]
}
```

| Status | Reason |
|--------|--------|
| 409 | Quiz already submitted |
| 404 | Quiz not found |
| 422 | Invalid request body |

---

### GET `/api/quiz/{quiz_id}/results`

Get detailed results for a completed quiz attempt.

**Response (200):**

```json
{
  "score": 85.0,
  "total": 20,
  "percentage": 85.0,
  "per_question_results": [
    {
      "question_id": "uuid-string",
      "question_text": "What is...",
      "options": ["A", "B", "C", "D"],
      "correct_index": 1,
      "difficulty": "medium",
      "blooms_level": "understand",
      "feedback_correct": "Right!",
      "feedback_incorrect": "Wrong because..."
    }
  ]
}
```

---

### GET `/api/quiz/by-job/{job_id}`

List all quizzes generated for a specific job.

**Response (200):**

```json
{
  "quizzes": [
    {
      "id": "uuid-string",
      "title": "Quiz: lecture.pdf",
      "created_at": "2026-03-09T12:00:00+00:00"
    }
  ]
}
```

## Pydantic Models

::: frontend.quiz_models
