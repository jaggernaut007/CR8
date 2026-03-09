# AGENTS.md
<!-- Universal agent memory. Loaded by Claude Code, GitHub Copilot, Cursor, Windsurf, and Codex.
     Keep under 100 lines. Task-specific guidance belongs in skills or .claude/rules/. -->

## Project Overview
CR8 — Adaptive Learning Pipeline. A 3-agent AI system (Ingest → Research → Generate) that
transforms university curriculum PDFs into market-enriched learning guides (PDF, PPT, scripts,
AI voiceover videos). Stack: Python 3.11+, FastAPI, LangGraph, OpenAI, ChromaDB, Tavily, Kokoro TTS.

## Tech Stack
- Language: Python 3.11+
- Pipeline: LangGraph state machine with 3 agents
- Web server: FastAPI + Uvicorn (port 8080)
- LLM: OpenAI (gpt-5.1 / gpt-5-mini / gpt-5-nano via model routing)
- Vector store: ChromaDB (local, all-MiniLM-L6-v2 embeddings)
- Web search: Tavily API
- Package manager: uv (Astral) — lockfile at `uv.lock`
- Testing: pytest — 834 backend tests + 69 Vitest + 10 Playwright E2E, zero real API calls (pytest-xdist parallel, ~42s)
- Linting: Ruff (line-length = 100)
- Docs: MkDocs Material — source in `mk-docs/`, config at `mkdocs.yml`
- Deployment: Docker + GCP Cloud Run

## Build & Test Commands
```bash
make install      # uv sync --all-extras
make dev          # FastAPI dev server → http://localhost:8080
make test         # uv run pytest -v  (834 backend tests, ~42s with xdist)
make e2e          # Playwright E2E tests (10 E2E tests: 5 auth + 5 content viewers)
make build-frontend # npm ci + npm run build → frontend/static/
make lint         # uv run ruff check .
make lint-fix     # uv run ruff check . --fix
make docs-serve   # mkdocs preview → http://localhost:8000
make docs-build   # mkdocs build --strict
make run ARGS="path/to/file.pdf"  # CLI pipeline
```

## Code Standards
- Place all external API calls (OpenAI, Tavily, HeyGen) in `backend/services/` only
- Use Pydantic models for all FastAPI request and response types
- Use typed `TypedDict` for all LangGraph state schemas in `backend/pipeline/state.py`
- Mock all external API calls in tests — the full test suite runs with zero real API calls
- Run `ruff check .` and confirm clean before marking any task complete
- Run `make test` and confirm all 834 backend tests (0 real API calls) pass before marking any task complete

## Code Quality (Enforced by Ruff + Agent Rules)
- **Short functions**: max 25 statements, max 5 args, max cyclomatic complexity 10 (see `.claude/rules/code-quality.md`)
- **Logging**: every module needs `logger = logging.getLogger(__name__)`; log function entry/exit at INFO, exceptions at ERROR with `exc_info=True`; use lazy `%s` formatting — never f-strings in log calls
- **Docstrings**: every module and public function needs a Google-style docstring
- **No print()**: use `logger.info()` instead (enforced by ruff T20)
- **No commented-out code**: delete dead code, git has history (enforced by ruff ERA001)
- **Tool verification**: always use tool calls to verify your work — read lint output, read test output, grep for patterns. Never assume code passes; check it.

## Testing Requirements
- All new features require tests before the task is marked complete
- Test naming: `test_[function]_[scenario]`
- Test files mirror source: `backend/tests/test_services.py` for `backend/services/`
- Use `@pytest.mark.slow` for any test taking over 1 second
- Use `hypothesis` for property-based tests, `syrupy` for snapshot regression tests
- Confirm tests pass by reading the test output — never assume they pass

## Definition of Done
A task is complete only when ALL of the following are true:
1. `make test` passes (all 834 backend tests (0 real API calls))
2. `make lint` passes (ruff clean)
3. Docs updated if any public behaviour changed
4. `PROGRESS.md` updated with what was done
5. `./scripts/init.sh` passes end-to-end

## Session Start Protocol
1. Read `PROGRESS.md` for current project state
2. Run `./scripts/init.sh` to verify the app is healthy
3. Verify MCP servers are connected (`/mcp`) — Context7, Playwright, Sequential Thinking
4. Fix any failures BEFORE starting new work

## Key Directories
```
backend/pipeline/   → LangGraph agents (ingest, research, generate) + state
backend/services/   → All external API wrappers (LLM, ChromaDB, Tavily, builders)
backend/prompts/    → Prompt templates (never put prompts inline in agents)
backend/evals/      → Evaluation framework with L1/L2 judges and CLI
frontend/           → FastAPI web server + route modules (port 8080)
frontend/react-app/ → React 19 SPA (Vite 7, Tailwind v4, Tanstack Query) — build with make build-frontend
mk-docs/            → MkDocs documentation source
docs/adr/           → Architecture Decision Records (read before structural decisions)
docs/research/      → Implementation research notes (read before using external APIs)
.claude/            → Agent skills, subagents, rules, and hooks
```

## MCP Server Usage
Agents have access to MCP tools for external capabilities:

| MCP Server | Tools | Used By |
|------------|-------|---------|
| **Context7** | `resolve-library-id`, `query-docs` | `research-assistant`, `docs-writer`, `test-writer`, `code-reviewer`, `debug-detective` |
| **Playwright** | `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_console_messages`, `browser_network_requests` | `code-reviewer`, `debug-detective`, `docs-writer` |
| **Sequential Thinking** | `sequentialthinking` | `adr-writer`, `prompt-optimizer`, `eval-judge`, `research-assistant`, `docs-writer` |
| **Snyk** | `snyk_test`, `snyk_code_scan`, `snyk_package_health_check` | `research-assistant`, `code-reviewer` |

**When to use each:**
- **Context7** — before writing code that uses any external library; before documenting library APIs
- **Playwright** — when reviewing or debugging frontend changes (localhost:8080)
- **Sequential Thinking** — when reasoning through architectural trade-offs for ADRs
- **Snyk** — when adding new dependencies (package health check), during code review (SAST scan), and when auditing dependency vulnerabilities

## Subagent Routing
Claude Code routes to these agents automatically when the situation matches:

| Situation | Agent | Model | MCP |
|-----------|-------|-------|-----|
| Before structural change (new dep, pipeline node, output format, model routing) | `adr-writer` | opus | Sequential Thinking |
| After running `python -m backend.evals compare` | `eval-judge` | opus | Sequential Thinking |
| When iterating on any prompt in `backend/prompts/` | `prompt-optimizer` | opus | Sequential Thinking |
| After every wave of implementation (write + verify tests) | `test-writer` | sonnet | Context7 |
| After every wave of implementation (quality + lint + architecture + Snyk scan) | `code-reviewer` | sonnet | Playwright, Context7, Snyk |
| When `make test` produces failures | `debug-detective` | sonnet | Playwright, Context7 |
| Before committing (update mk-docs, CHANGELOG, PM-Docs, AGENTS.md counts, PROGRESS.md, llms.txt) | `docs-writer` | sonnet | Context7, Playwright |
| Before using any external library or API (includes security assessment) | `research-assistant` | haiku | Context7, Sequential Thinking, Snyk |

### Wave Protocol
A "wave" is any completed unit of work — a feature, fix, refactor, phase, or version milestone. After completing each wave, run agents in this order:
1. **`test-writer`** — write/update tests for the changed code
2. **`code-reviewer`** — review quality, lint, architecture (skip Snyk scan per-wave)
3. Fix any blocking issues found by the reviewer
4. **`docs-writer`** — update documentation (run once before commit, not per-wave unless docs-heavy)

**Pre-commit** (after all waves are done):
5. **`code-reviewer`** with Snyk enabled — `snyk_code_scan` + `snyk_test` (if deps changed)

**Snyk budget**: ~100 free tests/month. Reserve for pre-commit scans and new dependency evaluations.
Do NOT run Snyk on every wave — use ruff + manual security checklist for per-wave reviews.

## Version Management
- Use `cz commit` for all commits (conventional commit format, enforced by pre-commit hook)
- Use `cz bump --changelog` to bump version and update `CHANGELOG.md`
- Current version tracked in `pyproject.toml` → `[project] version`

## What the Agent Must Know Before Acting
- External library/API usage → check `docs/research/` first; create note if missing
- Architectural decisions → check `docs/adr/` before changing structure
- Prompt changes → run eval comparison (`python -m backend.evals`) before committing
- Environment → requires `.env` file with OPENAI_API_KEY, TAVILY_API_KEY (see `.env.example`)
