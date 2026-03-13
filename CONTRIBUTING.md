# Contributing to CR8

> Agent-readable pattern reference. Read this before implementing new features.

## Architecture Rules

### Where code goes
| What you're adding | Where it goes |
|--------------------|---------------|
| New pipeline step / agent | `backend/pipeline/` |
| New external API integration | `backend/services/` (one file per integration) |
| New output format | `backend/services/[format]_builder.py` + `backend/prompts/[format].py` |
| New auth or auth-adjacent route | `frontend/auth_routes.py` |
| New job management route | `frontend/job_routes.py` |
| New quiz route | `frontend/quiz_routes.py` |
| New middleware (auth, security headers, rate limiting) | `frontend/middleware.py` |
| New UI template | `frontend/templates/` |
| New prompt string | `backend/prompts/` (never inline) |
| New config value | `backend/config.py` via Pydantic Settings |

### What never goes where
- External API calls never go outside `backend/services/`
- Prompt strings never go inline in agent files
- Hardcoded model names, ports, or API keys never go in code — always use `settings`

## Coding Standards

### Python
- Type hints on all function signatures
- Pydantic models for all FastAPI request/response types
- Typed `TypedDict` for all LangGraph state schemas
- Line length: 100 chars (enforced by Ruff)
- Run `make lint` before every commit — Ruff must pass cleanly

### Code Quality (Enforced by Ruff + Agent Rules)

**Short functions:**

| Constraint | Limit | Ruff Rule |
|------------|-------|-----------|
| Max statements per function | 25 | PLR0915 |
| Max arguments per function | 5 | PLR0913 |
| Max cyclomatic complexity | 10 | C901 |
| Max branches per function | 12 | PLR0912 |
| Max return statements | 6 | PLR0911 |

If a function exceeds any limit, refactor into smaller helpers. Use early returns to flatten nesting.

**Logging (mandatory in all modules):**

```python
import logging
logger = logging.getLogger(__name__)
```

- Log function entry/exit at INFO with key params
- Log exceptions at ERROR with `exc_info=True`
- Log external API calls before (INFO) and after (INFO/ERROR)
- Use lazy formatting: `logger.info("Built %d slides", count)` — never f-strings in log calls
- Never use `print()` in production code — use the logger (enforced by T20)

**Comments and docstrings:**

- Every module needs a module-level docstring
- Every public function needs a Google-style docstring (Args, Returns)
- Inline comments for non-obvious logic only — don't restate the code
- Never leave commented-out code (enforced by ERA001)

**Code cleanliness:**

- No mutable default arguments (B006)
- No builtin shadowing — never name variables `list`, `dict`, `type`, `id` (A)
- Use modern Python syntax — `dict` not `typing.Dict`, `X | None` not `Optional[X]` (UP)
- Clean return patterns — no superfluous `else` after `return` (RET)
- Simplify where possible — merge `isinstance()`, use `contextlib.suppress()` (SIM)

### Ruff Rule Categories

The full set of enabled Ruff rules (see `pyproject.toml`):

| Code | Category | What It Catches |
|------|----------|----------------|
| E/W/F | Defaults | Syntax errors, whitespace, unused imports |
| UP | pyupgrade | Outdated Python syntax |
| B | bugbear | Common bugs (mutable defaults, bad except) |
| A | builtins | Shadowing builtin names |
| T20 | print | `print()` in production code |
| RET | return | Messy return patterns |
| SIM | simplify | Code that could be simplified |
| PIE | pie | Misc Python anti-patterns |
| C90 | McCabe | Cyclomatic complexity > 10 |
| G | logging-format | f-strings in log calls |
| ERA | eradicate | Commented-out dead code |
| PLR | pylint | Function size/complexity limits |
| RUF | ruff | Ruff-specific cleanup rules |

Auto-fix safe violations: `ruff check . --fix`

### Testing
- Every new feature requires corresponding tests in `backend/tests/` or `frontend/tests/`
- All external API calls mocked — zero real API calls in the test suite
- Test naming: `test_[function]_[scenario]`
- Use `hypothesis` for property-based testing, `syrupy` for snapshot regression
- Run `make test` and read the output — all 1063 tests must pass

## Workflow Before Committing

Run `/commit-ready` to validate the full checklist automatically, or follow manually:

1. **External library/API?** Check `docs/research/INDEX.md` — create research note if missing
2. **Architectural change?** Check `docs/adr/` — create new ADR if making structural decisions
3. **Prompt change?** Run `python -m backend.evals run_ab` and document results
4. **All checks**: `make lint && make test`
5. **Update**: `PROGRESS.md` with what was done

## Available Skills

| Skill | Invoke | Purpose |
|-------|--------|---------|
| `/commit-ready` | "am I ready to commit" | Full pre-commit checklist gate |
| `/coverage-report` | "what's my coverage" | Find untested modules, route to test-writer |
| `/new-feature` | "scaffold a feature" | Ordered file creation checklist with agent routing |
| `/session-handoff` | "wrap up" | Read/write session state to PROGRESS.md |

## Commit Style

Follow Conventional Commits:
```
feat: add PPT export for adaptive assessment format
fix: handle empty PDF uploads without crashing ingest agent
docs: update services/llm.md with new model routing table
chore: bump langgraph to 0.2.x
```

Include test counts in feat commits: `feat: add quiz agent pipeline (928 → 1063 tests)`

## Pull Request Checklist
- [ ] `make lint` passes (ruff clean)
- [ ] `make test` passes (all tests)
- [ ] `PROGRESS.md` updated
- [ ] Docs updated if public API/behaviour changed
- [ ] ADR created if architectural decision was made
- [ ] Research note created if new external library was integrated

## Video Pipeline Development

The video pipeline uses `VIDEO_PROVIDER=kokoro` (default) for local TTS + ffmpeg rendering:

| Env Var | Default | Purpose |
|---------|---------|---------|
| `VIDEO_PROVIDER` | `kokoro` | Video provider (kokoro, heygen, synthesia) |
| `VIDEO_DEVICE` | `auto` | TTS device (auto, cpu, mps, cuda) |
| `VIDEO_MAX_WORKERS` | `12` | Parallel ffmpeg workers |
| `GPU_SERVICE_URL` | (empty) | GPU Cloud Run URL for offloading (optional) |
| `GCS_BUCKET` | `cr8-jobs` | GCS bucket for CPU↔GPU data transfer |

When `GPU_SERVICE_URL` is set, video rendering is offloaded to a GPU service (NVIDIA L4). Otherwise, it runs locally.

## Frontend Development

The frontend is a React 19 SPA (Vite 7, Tailwind v4, glassmorphism design) served as static files by FastAPI. A Jinja2 fallback exists when the SPA is not built. See `docs/adr/ADR-010-react-spa-frontend.md` for architecture decisions.

The frontend package is split into focused modules (Wave 3 restructure):

| Module | Responsibility |
|--------|---------------|
| `frontend/app.py` | App factory, lifespan, CORS/middleware wiring — no route logic |
| `frontend/middleware.py` | Auth enforcement, security headers, rate limiting, session store |
| `frontend/auth_routes.py` | All `/api/auth/*` routes |
| `frontend/job_routes.py` | All job management routes (`/api/upload`, `/api/start`, etc.) |
| `frontend/quiz_routes.py` | All `/api/quiz/*` routes (start, question, answer, results, attempts) |

When adding a new route, choose the appropriate sub-module rather than adding to `app.py`.
