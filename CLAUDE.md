# CLAUDE.md
<!-- Claude Code-specific memory. Kept lean — universal rules live in AGENTS.md.
     This file uses @import to pull in skill files on demand.
     Claude Code injects this into every session via system-reminder. -->

@import AGENTS.md

## Claude-Specific Behaviours

### Subagent Routing
- Use the **Explore** subagent for read-only codebase search — keeps navigation out of main context
- Use the **Plan** subagent before implementing anything non-trivial — always plan before coding
- Do NOT spawn subagents for simple single-file changes

### Context Management
- When context feels crowded or you've been working for many turns, stop and write a summary to `PROGRESS.md` before continuing
- Start fresh sessions for new features — don't continue sprawling threads
- If you are uncertain about a past decision, check `docs/adr/` before guessing

### Testing Protocol
- Always use tool calls to verify your work — read test output, don't assume it passes
- For web features, use browser automation to test as a real user would
- Run `./scripts/init.sh` at session start and after major changes

### Hallucination Prevention
- For any external library or API, try **Context7 MCP first** (`resolve-library-id` → `get-library-docs`) — it covers LangGraph, FastAPI, ChromaDB, python-pptx, fpdf2, MoviePy, PyMuPDF
- If Context7 doesn't cover it, check `docs/research/` for an existing research note
- If no research note exists, perform a web search for the current official docs before writing implementation code
- Pin library versions in all research queries — do not assume the latest API matches training data

### MCP Servers
- **Context7** — version-specific library docs. Use before web search for any library question.
- **Playwright** — browser automation. Use to test web UI at localhost:8080.
- **Sequential Thinking** — structured reasoning for architecture decisions.
- **Nexus-MCP** — unified code intelligence: hybrid search (vector + BM25 + graph via RRF), structural analysis (callers, callees, impact, complexity), and semantic memory. Replaces CodeGrok + code-graph-mcp. Use `search` for "how does X work?", `find_callers`/`impact` for "what calls Y?", `explain` for combined understanding, `remember`/`recall` for persistent project knowledge. 15 tools, fully local, token-budgeted (summary/detailed/full).

## Skills Available
<!-- Skills are loaded on-demand — only metadata is preloaded -->
- `session-handoff` — write/read session state between conversations
- `commit-ready` — pre-commit verification (lint + test + docs build)
- `coverage-report` — generate and display test coverage summary
- `new-feature` — scaffold a new feature with service, tests, and docs
