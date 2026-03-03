# Changelog

All notable changes to CR8 are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [0.3.0] — 2026-03-03

### Added
- 6 new Claude Code subagents in `.claude/agents/`:
  - `adr-writer` (opus) — writes Architecture Decision Records before structural changes
  - `eval-judge` (opus) — produces SHIP/HOLD/ITERATE verdicts from eval comparison reports
  - `prompt-optimizer` (opus) — iterates on prompts in `backend/prompts/` using eval feedback
  - `test-writer` (sonnet) — writes pytest tests following CR8 mock conventions
  - `debug-detective` (sonnet) — diagnoses and fixes failing tests
  - `docs-writer` (sonnet) — updates `mk-docs/` pages for staged code changes before commits
- Subagent routing table in `AGENTS.md` for automatic dispatch without user prompting
- Commitizen semantic versioning (`commitizen>=3.0`) with conventional-commit format
- `[tool.commitizen]` configuration in `pyproject.toml`
- Pre-commit lint gate (blocks commits with ruff failures) in `.claude/hooks.json`
- Docs-staleness warning hook (warns when backend files staged without doc updates)
- `.claude/hooks/pre-commit-docs-check.sh` — shell script for docs staleness check
- Commitizen usage docs in `mk-docs/getting-started/developer-workflow.md`

---

## [0.2.0] — 2026-03-03

### Added
- Agent-readiness scaffolding: `AGENTS.md`, `PROGRESS.md`, `CLAUDE.local.md`, `feature_list.json`
- `scripts/init.sh` smoke test (ruff + 362 tests + docs build)
- `.claude/agents/code-reviewer.md` (sonnet) and `research-assistant.md` (haiku)
- `.claude/rules/api-standards.md` and `test_standards.md`
- Pre-commit ruff lint hook (Stop + PostToolUse) in `.claude/hooks.json`
- MkDocs documentation site (49 pages, Material theme, `mk-docs/` directory)
- `mk-docs/llms.txt` — machine-readable docs index
- `docs/research/INDEX.md` and `docs/agentic-guide.md`
- `backend/CLAUDE.md` and `frontend/CLAUDE.md` (lazy-loaded subdirectory rules)
- `CONTRIBUTING.md` and directory READMEs

### Fixed
- 34 pre-existing ruff lint errors resolved across codebase

---

## [0.1.0] — 2026-03

### Added
- 3-agent LangGraph pipeline: Ingest → Research → Generate
- Output formats: PDF, PPT, video script, HeyGen AI avatar video
- FastAPI web server (`frontend/`) with bcrypt session authentication on all routes
- 362-test suite with zero real API calls (~27s runtime)
- Evaluation framework: L1 structural judges + L2 LLM judges + A/B comparison CLI
- Docker containerisation + GCP Cloud Run deployment configuration
- Multi-model routing: nano/mini/premium tiers with task-specific temperature presets
- Parallel execution across all three pipeline agents (`ThreadPoolExecutor`)
- Domain-scoped prompts with `curriculum_scope` flowing through entire pipeline
- ChromaDB result caching, map-reduce summarization for long files
- Module validation with retry (up to 2 retries for failed generations)
- Rich PDF rendering: bold, italic, code blocks with Courier font on gray background
- PPT gap analysis builder with 6 slide types and CR8 design tokens
- Slide-synced video script generation (`SCRIPT_FROM_SLIDES` prompt)
