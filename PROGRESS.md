# PROGRESS.md
<!-- Agent cross-session memory. Read at the start of every session.
     Updated at the end of every session using the session-handoff skill. -->

## Current Status
**Last updated:** 2026-03-03
**Overall project phase:** Stable baseline — agent-readiness setup COMPLETE

## What's Working
- Full 3-agent pipeline end-to-end (Ingest → Research → Generate)
- All output formats: PDF, PPT, video script, AI avatar video (HeyGen)
- 362-test suite — all passing, zero real API calls in suite (~27s)
- Authentication (bcrypt session auth on all protected routes)
- Docker containerisation + GCP Cloud Run deployment
- Evaluation framework (L1 structural + L2 LLM judges, A/B comparison CLI)
- MkDocs documentation site (49 pages, Material theme)
- **Agent-readiness setup — fully complete and verified:**
  - AGENTS.md ✅, PROGRESS.md ✅, CLAUDE.local.md ✅, feature_list.json ✅
  - scripts/init.sh ✅ (all 4 checks pass: ruff ✓, 362 tests ✓, docs ✓)
  - .claude/agents/ ✅ (code-reviewer + research-assistant)
  - .claude/rules/ ✅ (api-standards + test_standards)
  - .claude/hooks.json ✅ (Stop: ruff; PostToolUse: per-file ruff)
  - backend/CLAUDE.md ✅, frontend/CLAUDE.md ✅
  - CONTRIBUTING.md ✅
  - Directory READMEs ✅ (backend/, frontend/, pipeline/, services/)
  - docs/research/INDEX.md ✅, docs/agentic-guide.md ✅
  - mk-docs/getting-started/developer-workflow.md ✅
  - docs/agentic-setup-template.md ✅
  - mk-docs/llms.txt ✅
  - Makefile: lint + lint-fix targets ✅
  - Pre-existing lint issues fixed: 34 ruff errors resolved ✅

## In Progress
- Nothing — clean baseline ready for next feature work

## Known Broken / Blocked
- None

## Next Steps (Prioritised)
1. Write first ADR: pipeline architecture decision (`docs/adr/ADR-001-langgraph-pipeline.md`)
2. Write first research note: OpenAI model routing (`docs/research/openai-model-routing.md`)
3. Investigate adaptive assessment feature (see `PM-Docs/` for spec)
4. Plan real frontend (React/Next.js — see `docs/research/frontend-framework.md` when ready)

## Recent Decisions
| Date | Decision | Rationale | ADR |
|------|----------|-----------|-----|
| 2026-03 | Moved docs from `Docs/` → `mk-docs/` | Avoid conflict with MkDocs `docs_dir` default | — |
| 2026-03 | March hardening: 144 → 362 tests | Hypothesis + syrupy added for property-based and snapshot testing | — |
| 2026-03 | Set up agentic scaffolding (AGENTS.md, skills, hooks) | Optimise Claude Code productivity | — |

## Environment Notes
- Dev server: `make dev` → http://localhost:8080
- Docs preview: `make docs-serve` → http://localhost:8000
- Tests: `make test` → all 362 pass (~60s)
- Requires: `.env` file with OPENAI_API_KEY, TAVILY_API_KEY (copy from `.env.example`)
