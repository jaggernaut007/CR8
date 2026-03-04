# Contributing to CR8

> Agent-readable pattern reference. Read this before implementing new features.

## Architecture Rules

### Where code goes
| What you're adding | Where it goes |
|--------------------|---------------|
| New pipeline step / agent | `backend/pipeline/` |
| New external API integration | `backend/services/` (one file per integration) |
| New output format | `backend/services/[format]_builder.py` + `backend/prompts/[format].py` |
| New FastAPI route | `frontend/app.py` |
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

### Testing
- Every new feature requires corresponding tests in `backend/tests/` or `frontend/tests/`
- All external API calls mocked — zero real API calls in the test suite
- Test naming: `test_[function]_[scenario]`
- Use `hypothesis` for property-based testing, `syrupy` for snapshot regression
- Run `make test` and read the output — all 426 tests must pass

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

Include test counts in feat commits: `feat: add video script streaming (426 → 439 tests)`

## Pull Request Checklist
- [ ] `make lint` passes (ruff clean)
- [ ] `make test` passes (all tests)
- [ ] `PROGRESS.md` updated
- [ ] Docs updated if public API/behaviour changed
- [ ] ADR created if architectural decision was made
- [ ] Research note created if new external library was integrated

## Frontend Development

The current `frontend/` is a prototype FastAPI/HTML UI. A proper React frontend is planned.
Before starting frontend work, create `docs/research/frontend-framework.md` to document
the chosen tech stack and check `docs/adr/` for prior decisions.
