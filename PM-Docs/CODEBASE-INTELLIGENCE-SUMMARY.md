# Code Intelligence & Project Management: Quick Reference

**Full research:** `docs/research/code-intelligence-tools.md`
**Date:** 2026-03-06
**For:** Planning v0.5 Phase 2 onwards

---

## TL;DR Recommendation

**UPDATE (2026-03-12):** CodeGrok + code-graph-mcp have been consolidated into **Nexus-MCP** — a single unified server with hybrid search (vector + BM25 + graph), structural analysis, and semantic memory. 15 tools, <350MB RAM, fully local, MIT licensed.

Add **Nexus-MCP** (code intelligence) + **GitHub Projects V2** (issue tracking) + **token optimization strategies** to improve codebase knowledge and reduce context spending by 40-60%.

**Effort:** 30 min setup (already installed at `~/dev/Nexus-MCP/`)
**Status:** DONE — configured in `.claude/mcp.json`

---

## Problem Statement

- **Code knowledge:** Agent doesn't understand codebase without loading full files (wastes tokens)
- **Feature tracking:** Features scattered across 3 markdown files (~1000 lines); hard to query
- **Token waste:** 50-60K tokens per response; 40-50% of window is boilerplate/stale context

---

## Solution: 3-Part Combo

### 1. Nexus-MCP (Unified Code Intelligence)

**What:** Hybrid code search + structural analysis + semantic memory in one server. "Find all code related to video building" → returns `video_builder.py`, `gpu_client.py`, `tts_engine.py` snippets via vector+BM25+graph fusion, re-ranked with FlashRank. Replaces the previous CodeGrok + code-graph-mcp dual setup.

**Setup:** Already installed at `~/dev/Nexus-MCP/`
```bash
cd ~/dev/Nexus-MCP
./setup.sh  # Python 3.10+ required (one-time)
```

**15 Tools:**
- `search` — hybrid search (vector + BM25 + graph fusion via RRF)
- `find_symbol`, `find_callers`, `find_callees` — structural graph queries
- `analyze`, `impact`, `explain` — complexity, change impact, combined understanding
- `overview`, `architecture` — project-level analysis
- `remember`, `recall`, `forget` — persistent semantic memory
- `index`, `status`, `health` — indexing and diagnostics

**Token savings:** 10-100x per query (token-budgeted responses)
- `summary` ~500 tokens — counts, scores, file:line pointers
- `detailed` ~2,000 tokens — signatures, types, line ranges, docstrings
- `full` ~8,000 tokens — full code snippets, relationships, metadata

**Why it's safe:**
- MIT license
- Local storage (`.nexus/` directory, gitignored)
- No external APIs, no cloud dependencies
- <350MB RAM, ONNX Runtime embeddings

**Language support:** 25+ languages (Python, JavaScript, TypeScript, Go, Java, Rust, C, C++, and more)

---

### 2. GitHub Projects V2 MCP (Issue Tracking)

**What:** Manage GitHub Projects board via Claude. Link issues to feature board for active sprint.

**Setup:** 5 minutes
```bash
# In Claude Code MCP settings, add:
{
  "mcpServers": {
    "github": {
      "command": "..."  # configure with GitHub PAT
    }
  }
}
```

**Usage:** Create "v0.5 Phase 2" board, link frontend issues, let Claude Code query/prioritize issues.

**Why:** Code already on GitHub; keeps project management close to code.

**Limitation:** Cannot manage Kanban columns via API (minor; read/filter issues works great).

---

### 3. Token Optimization Strategies (No Tools)

These are behaviors, not tools. Impact: 40-60% token reduction.

#### A. Use `/clear` Between Unrelated Work
When switching from backend to frontend → `/clear` to start fresh session.
- Example: After GPU service work (session 1), `/clear`, start React SPA work (session 2)
- Saves: 20-30% of tokens by not carrying stale context

#### B. Keep CLAUDE.md Under 500 Lines
CR8 already does this (90 lines). Continue pattern.
- Skills go in `.claude/agents/*.md` (load on-demand only)
- Saves: 10% per response

#### C. Use Plan Mode for Multi-File Changes
Ask Claude to "plan" before implementing large changes.
- Example: Before adding DB layer: `plan: add asyncpg + 6 CRUD tables`
- Agent proposes strategy, you validate, then it implements
- Saves: 40-60% total tokens for complex changes

#### D. Three-Session Architecture (Optional)
Instead of one bloated session (180K tokens), maintain 3 focused sessions (40K each):
- Session 1: Backend agent
- Session 2: Frontend agent
- Session 3: Docs/Infrastructure agent

CR8 already does this via code-reviewer, test-writer, docs-writer agents. Formalize the pattern.

#### E. Extended Thinking Control
Extended thinking enabled by default (31,999 token budget). Disable for trivial fixes.
- Use `/model` to check; lower budget or disable for quick edits
- Saves: 10-20% on simple tasks

---

## Implementation Timeline

### DONE (2026-03-12)

- [x] Install Nexus-MCP (`~/dev/Nexus-MCP/`)
- [x] Configure in `.claude/mcp.json` (replaces CodeGrok + code-graph-mcp)
- [x] Update all docs (AGENTS.md, CLAUDE.md, ADR-011, agentic-guide, developer-workflow)
- [x] Update `.gitignore` (`.nexus/` directory)
- [x] Update `scripts/init.sh` health check
- [x] Update `Makefile` reindex target

### Remaining

- [ ] Add GitHub Projects V2 MCP, create sprint board, link issues
- [ ] Adopt `/clear` pattern: separate backend/frontend work into 2 sessions
- [ ] Run initial Nexus-MCP index on CR8 codebase and validate search quality

---

## What NOT to Do

- ❌ **Linear MCP:** Too expensive ($20/person/month), overkill for 2-person team
- ❌ **CodePathfinder:** AGPL license incompatible with CR8's deployment model
- ❌ **Milvus/CodeIndexer:** Requires extra infrastructure; overkill for 15K LoC backend
- ❌ **Plane:** Self-hosted project management; Notion simpler
- ❌ **Replace Markdown with Database:** Keep markdown for quick diffs/reviews; use Notion for agent queries

---

## Expected Impact

| Metric | Current | After | Improvement |
|--------|---------|-------|-------------|
| Avg context/response | 50-60K | 25-30K | **45-50% less** |
| Response time | 8-12s | 3-5s | **60% faster** |
| Code search friction | Manual digging | 1-2 Nexus-MCP queries | **80% easier** |
| Feature query speed | Manual grep | Notion DB query | **70% faster** |
| Phase transitions | High (stale context) | Low (/clear resets) | **50% less overhead** |

---

## Cost Analysis

| Tool | Cost | Setup | Maintenance |
|------|------|-------|------------|
| Nexus-MCP | Free | 30 min (done) | 5 min/week (reindex) |
| GitHub Projects V2 | Free | 5 min | 10 min/week |
| Notion MCP | Included (already $) | 10 min | 5 min/week |
| Token optimization | Free | 0 min | 0 min (behavior change) |
| **Total** | **$0** | **1 hour** | **25 min/week** |

---

## FAQ

**Q: Will Nexus-MCP slow down my iterations?**
A: No. First index ~2-5 min (one-time). After that, incremental indexing only processes changed files. Queries are instant + hugely reduce token cost.

**Q: Do I have to move to GitHub Projects?**
A: No. It's optional and complementary to Notion. Use GitHub Projects for active sprint tracking, Notion for backlog.

**Q: What if I use Cursor instead of Claude Code?**
A: All tools are MCP-based, work with any MCP client (Cursor, Windsurf, Continue, Zed, Claude Desktop).

**Q: Why Nexus-MCP instead of CodeGrok + code-graph-mcp?**
A: Nexus-MCP consolidates both into one server with additional benefits: hybrid fusion (vector+BM25+graph), token-budgeted responses, semantic memory, impact analysis, and architecture overview. One process, <350MB RAM, 15 tools.

**Q: How much token savings can I expect?**
A: 40-60% with full implementation. Nexus-MCP alone = 30-50% (hybrid search is more precise than vector-only). Token optimization strategies = 20-30%.

---

## Reading List

- **Full research:** `docs/research/code-intelligence-tools.md` (15 min read)
- **Nexus-MCP:** https://github.com/jaggernaut007/Nexus-MCP (installed at `~/dev/Nexus-MCP/`)
- **ADR-011:** `docs/adr/ADR-011-code-knowledge-graph.md` (decision record)
- **Claude Code token optimization:** https://code.claude.com/docs/en/costs (5 min read)
- **GitHub Projects V2 MCP:** https://github.com/github/github-mcp-server (5 min setup)

---

**Next steps:** Review this summary, then read the full research note before Phase 2 sprint planning.
