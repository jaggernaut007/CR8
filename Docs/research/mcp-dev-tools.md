# Research: MCP Dev Tools for Claude Code

**Date researched:** 2026-03-04
**Library version:** Context7 (latest), GitHub MCP (latest), Playwright MCP v0.0.68, Sequential Thinking (latest), FastMCP v3.1.0, Sentry MCP (latest)
**Researched by:** Claude Code research-assistant agent
**Status:** Current

---

## Question Being Answered

Which MCP servers should CR8 install to improve developer workflow, and are the setup commands in `PM-Docs/MCP_Integration_Plan.md` still correct?

> How do we configure MCP servers for a Python/FastAPI + React project using Claude Code?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| Context7 GitHub | https://github.com/upstash/context7 | 2026-03-04 |
| GitHub MCP Server | https://github.com/github/github-mcp-server | 2026-03-04 |
| GitHub MCP Changelog (Jan 2026) | https://github.blog/changelog/2026-01-28-github-mcp-server-new-projects-tools-oauth-scope-filtering-and-new-features/ | 2026-03-04 |
| Playwright MCP | https://github.com/microsoft/playwright-mcp | 2026-03-04 |
| Sequential Thinking MCP | https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking | 2026-03-04 |
| FastMCP Framework | https://github.com/PrefectHQ/fastmcp | 2026-03-04 |
| FastAPI-MCP | https://github.com/tadata-org/fastapi_mcp | 2026-03-04 |
| Sentry MCP Docs | https://docs.sentry.io/product/sentry-mcp/ | 2026-03-04 |
| MCP Registry | https://registry.modelcontextprotocol.io/ | 2026-03-04 |

## What We Found

### Phase 1 — Config-Only Installs (verified correct)

```bash
# Context7 — version-specific library docs (hallucination prevention)
claude mcp add context7 -- npx -y @upstash/context7-mcp

# GitHub MCP — PR management, issues, CI status
claude mcp add --scope user --transport http github https://api.githubcopilot.com/mcp/

# Playwright MCP — browser automation, E2E testing
claude mcp add playwright -- npx -y @playwright/mcp@latest
```

### Phase 2 — Config-Only

```bash
# Sequential Thinking — structured step-by-step reasoning
claude mcp add --scope user sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking
```

### Phase 2 — Code Change (deferred to v0.5)

FastAPI-MCP requires mounting in `frontend/app.py`. Two options:
- `fastapi-mcp>=0.1` — original plan, zero-config auto-generator
- `fastmcp>=3.1` — newer (March 2026), more flexible Python MCP framework

### Phase 3 — When Deploying

```bash
# Sentry MCP — error monitoring (after Sentry is set up on GCP)
claude mcp add --scope user --transport http sentry https://mcp.sentry.dev/mcp
```

### Key API Methods / Concepts

| MCP Server | Key Tools | Notes |
|------------|-----------|-------|
| Context7 | `resolve-library-id`, `get-library-docs` | Covers LangGraph, FastAPI, ChromaDB, python-pptx, fpdf2, MoviePy, PyMuPDF. Token limit configurable (default 5000). |
| GitHub MCP | `projects_list`, `projects_get`, PR/issue CRUD | January 2026 update: consolidated Projects tools (23k token reduction). OAuth scope filtering auto-hides tools. |
| Playwright MCP | `browser_navigate`, `browser_click`, `browser_snapshot`, `browser_screenshot` | Uses accessibility snapshots by default (no screenshots needed). 143 device emulations. Cross-browser. |
| Sequential Thinking | `sequentialthinking` | Numbered steps with branching and revision. Dynamic step count. |
| FastMCP | `FastMCP(app)` or custom tools | v3.1.0 (March 2026). Can bootstrap from FastAPI app or build standalone MCP server. |
| Sentry MCP | Issue retrieval, Seer AI analysis | OAuth auth. Free tier available. |

### Configuration Required

All Phase 1+2 servers need Node.js >= v18 (for npx). No API keys required for basic use.

```bash
# Verify Node.js version
node --version  # must be >= 18

# After install, verify in Claude Code
/mcp  # all servers should show green
```

GitHub MCP authentication:
```bash
# Option A: OAuth (recommended)
# Authenticate via /mcp → select GitHub → browser OAuth flow

# Option B: Personal Access Token
claude mcp add --scope user --env GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx github -- npx -y @github/mcp-server
# Token scopes needed: repo, read:org, read:project
```

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| Knowledge Graph Memory MCP | CR8 already has 3-layer memory (PROGRESS.md, session-handoff, MEMORY.md) |
| Linear MCP | Project uses GitHub Issues, not Linear |
| Docker MCP | Makefile handles Docker; redundant |
| Desktop Commander MCP | Fully redundant with Claude Code built-in tools |
| GitMCP | Context7 covers the same need (library docs injection) |
| Apidog MCP | FastAPI-MCP is more relevant for CR8's own API |
| Slack MCP | CR8 doesn't use Slack |
| AWS MCP | CR8 deploys to GCP, not AWS |
| Pytest MCP | Community-maintained, not mature enough yet. Revisit later. |

## Known Gotchas / Edge Cases

- **GitHub MCP (Jan 2026 breaking change)**: Projects API consolidated — old `get_project`/`update_project` tools replaced by `projects_list`/`projects_get`. Old documentation may reference deprecated tools.
- **Playwright MCP**: Rapid release cycle (~every few days). Pin `@latest` is fine since no breaking changes observed, but be aware of churn.
- **Context7**: Free tier has rate limits. Optional OAuth flow for higher limits. Also supports remote mode via `https://mcp.context7.com/mcp` but local npx is faster.
- **FastMCP vs fastapi-mcp**: Two different packages. `fastmcp` (PrefectHQ) is the more active framework (v3.1, ~70% of MCP servers use it). `fastapi-mcp` (tadata-org) is simpler but less flexible. Recommend `fastmcp` for v0.5.
- **Sequential Thinking**: No version pinning available — follows MCP ecosystem versioning. No breaking changes expected.

## Decision Made

Based on this research, we will:
> 1. Install Phase 1 (Context7, GitHub, Playwright) and Phase 2 config-only (Sequential Thinking) immediately — all verified correct.
> 2. Defer FastAPI-MCP to v0.5, using `fastmcp>=3.1` instead of the originally planned `fastapi-mcp>=0.1`.
> 3. Defer Sentry MCP to Phase 3 (when Sentry is set up on GCP Cloud Run).
> 4. Update research-assistant agent to use Context7 as fast path before web search.

## Files This Affects

- `CLAUDE.md` — add MCP section, update hallucination prevention to reference Context7
- `AGENTS.md` — add `/mcp` verification to Session Start Protocol
- `.claude/agents/research-assistant.md` — add Context7 as Step 0 (fast path)
- `CLAUDE.local.md` — add MCP status reference
- `PM-Docs/MCP_Integration_Plan.md` — check off completed items, add research findings
- `PM-Docs/roadmap.md` — note MCP Phase 1+2 complete

---
*If this research is more than 6 months old or any MCP server has had a major version bump, re-verify before implementing.*
