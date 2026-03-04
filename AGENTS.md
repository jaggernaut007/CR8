# AGENTS.md
<!-- Universal agent memory. Loaded by Claude Code, GitHub Copilot, Cursor, Windsurf, and Codex.
     Keep under 100 lines. Task-specific guidance belongs in skills or .claude/rules/. -->

## Project Overview
CR8 — Adaptive Learning Pipeline. A 3-agent AI system (Ingest → Research → Generate) that
transforms university curriculum PDFs into market-enriched learning guides (PDF, PPT, scripts,
AI avatar videos). Stack: Python 3.11+, FastAPI, LangGraph, OpenAI, ChromaDB, Tavily.

## Tech Stack
- Language: Python 3.11+
- Pipeline: LangGraph state machine with 3 agents
- Web server: FastAPI + Uvicorn (port 8080)
- LLM: OpenAI (gpt-5.1 / gpt-5-mini / gpt-5-nano via model routing)
- Vector store: ChromaDB (local, all-MiniLM-L6-v2 embeddings)
- Web search: Tavily API
- Testing: pytest — 426 tests, zero real API calls
- Linting: Ruff (line-length = 100)
- Docs: MkDocs Material — source in `mk-docs/`, config at `mkdocs.yml`
- Deployment: Docker + GCP Cloud Run

## Build & Test Commands
```bash
make install      # pip install -e ".[dev]"
make dev          # FastAPI dev server → http://localhost:8080
make test         # pytest -v  (426 tests, ~60s)
make lint         # ruff check .
make lint-fix     # ruff check . --fix
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
- Run `make test` and confirm all 426 tests pass before marking any task complete

## Testing Requirements
- All new features require tests before the task is marked complete
- Test naming: `test_[function]_[scenario]`
- Test files mirror source: `backend/tests/test_services.py` for `backend/services/`
- Use `@pytest.mark.slow` for any test taking over 1 second
- Use `hypothesis` for property-based tests, `syrupy` for snapshot regression tests
- Confirm tests pass by reading the test output — never assume they pass

## Definition of Done
A task is complete only when ALL of the following are true:
1. `make test` passes (all 426 tests)
2. `make lint` passes (ruff clean)
3. Docs updated if any public behaviour changed
4. `PROGRESS.md` updated with what was done
5. `./scripts/init.sh` passes end-to-end

## Session Start Protocol
1. Read `PROGRESS.md` for current project state
2. Run `./scripts/init.sh` to verify the app is healthy
3. Verify MCP servers are connected (`/mcp`) — Context7, GitHub, Playwright, Sequential Thinking
4. Fix any failures BEFORE starting new work

## Key Directories
```
backend/pipeline/   → LangGraph agents (ingest, research, generate) + state
backend/services/   → All external API wrappers (LLM, ChromaDB, Tavily, builders)
backend/prompts/    → Prompt templates (never put prompts inline in agents)
backend/evals/      → Evaluation framework with L1/L2 judges and CLI
frontend/           → FastAPI web server + Jinja2 templates (port 8080)
mk-docs/            → MkDocs documentation source
docs/adr/           → Architecture Decision Records (read before structural decisions)
docs/research/      → Implementation research notes (read before using external APIs)
.claude/            → Agent skills, subagents, rules, and hooks
```

## Subagent Routing
Claude Code routes to these agents automatically when the situation matches:

| Situation | Agent | Model |
|-----------|-------|-------|
| Before structural change (new dep, pipeline node, output format, model routing) | `adr-writer` | opus |
| After running `python -m backend.evals compare` | `eval-judge` | opus |
| When iterating on any prompt in `backend/prompts/` | `prompt-optimizer` | opus |
| When adding new service or pipeline files | `test-writer` | sonnet |
| When `make test` produces failures | `debug-detective` | sonnet |
| Before committing (update mk-docs pages for staged changes) | `docs-writer` | sonnet |
| Before committing any changes (code quality check) | `code-reviewer` | sonnet |
| Before using any external library or API | `research-assistant` | haiku |

## Version Management
- Use `cz commit` for all commits (conventional commit format, enforced by pre-commit hook)
- Use `cz bump --changelog` to bump version and update `CHANGELOG.md`
- Current version tracked in `pyproject.toml` → `[project] version`

## What the Agent Must Know Before Acting
- External library/API usage → check `docs/research/` first; create note if missing
- Architectural decisions → check `docs/adr/` before changing structure
- Prompt changes → run eval comparison (`python -m backend.evals`) before committing
- Environment → requires `.env` file with OPENAI_API_KEY, TAVILY_API_KEY (see `.env.example`)
