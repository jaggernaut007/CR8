# Code Intelligence & Project Management: Quick Reference

**Full research:** `docs/research/code-intelligence-tools.md`
**Date:** 2026-03-06
**For:** Planning v0.5 Phase 2 onwards

---

## TL;DR Recommendation

Add **CodeGrok** (code intelligence) + **GitHub Projects V2** (issue tracking) + **token optimization strategies** to improve codebase knowledge and reduce context spending by 40-60%.

**Effort:** 1 hour setup, no budget required
**Timeline:** v0.5 Phase 2 (after React SPA done)

---

## Problem Statement

- **Code knowledge:** Agent doesn't understand codebase without loading full files (wastes tokens)
- **Feature tracking:** Features scattered across 3 markdown files (~1000 lines); hard to query
- **Token waste:** 50-60K tokens per response; 40-50% of window is boilerplate/stale context

---

## Solution: 3-Part Combo

### 1. CodeGrok MCP (Code Intelligence)

**What:** Semantic code search. "Find all code related to video building" → returns `video_builder.py`, `gpu_client.py`, `tts_engine.py` snippets, not entire files.

**Setup:** 30 minutes
```bash
git clone https://github.com/dondetir/CodeGrok_mcp
cd CodeGrok_mcp
./setup.sh  # Python 3.10+ required
```

**Token savings:** 10x per code search query
- Before: Load 20 files (5K tokens) to answer "how do we build videos?"
- After: Query CodeGrok (500 tokens)

**Why it's safe:**
- MIT license
- Local storage (.codegrok/ directory)
- No external APIs
- Single maintainer, active development

**Language support:** Python, JavaScript, TypeScript, C, C++, Go, Java, Kotlin, Bash

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

### v0.5 Phase 2 (React SPA Sprint, 2 weeks)

**Week 1:**
- [ ] Add CodeGrok MCP (.claude/mcp.json + setup)
- [ ] Run initial index (5K backend files, 2-5 min)
- [ ] Test 5 semantic searches ("how do we X?")
- [ ] Add GitHub Projects V2 MCP, create "v0.5 Phase 2" board, link 10+ issues

**Week 2:**
- [ ] Adopt `/clear` pattern: separate backend/frontend work into 2 sessions
- [ ] Test Plan mode on a 5-file refactor (expected 40-60% token savings)
- [ ] Document in CLAUDE.md

### v0.5 Post-Launch (1 week)

- [ ] Upgrade Notion: create Feature tracking database (Status | Phase | Owner | Blocker | Link)
- [ ] Export PROGRESS.md into Notion (one-time)
- [ ] Keep PROGRESS.md as session cache (read-only from Notion export)

### Optional: v0.5 Phase 3 / v0.6 (Future)

- [ ] Add code-graph-mcp (multi-language call graphs) if needed
  - Requires Python 3.12 (CR8 currently 3.11)
  - Complements CodeGrok for "show me all callers of function X" queries

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
| Code search friction | Manual digging | 1-2 CodeGrok queries | **80% easier** |
| Feature query speed | Manual grep | Notion DB query | **70% faster** |
| Phase transitions | High (stale context) | Low (/clear resets) | **50% less overhead** |

---

## Cost Analysis

| Tool | Cost | Setup | Maintenance |
|------|------|-------|------------|
| CodeGrok | Free | 30 min | 5 min/week (reindex) |
| code-graph-mcp | Free | 15 min | 5 min/week |
| GitHub Projects V2 | Free | 5 min | 10 min/week |
| Notion MCP | Included (already $) | 10 min | 5 min/week |
| Token optimization | Free | 0 min | 0 min (behavior change) |
| **Total** | **$0** | **1 hour** | **25 min/week** |

---

## FAQ

**Q: Will CodeGrok slow down my iterations?**
A: No. First index ~2-5 min (one-time). After that, queries are instant + hugely reduce token cost.

**Q: Do I have to move to GitHub Projects?**
A: No. It's optional and complementary to Notion. Use GitHub Projects for active sprint tracking, Notion for backlog.

**Q: What if I use Cursor instead of Claude Code?**
A: All tools are MCP-based, work with any MCP client (Cursor, Windsurf, Continue, Zed, Claude Desktop).

**Q: Will Python 3.10 requirement for CodeGrok break CI?**
A: No. CR8 uses 3.11+, both satisfy CodeGrok's requirement. code-graph-mcp needs 3.12 (optional for later).

**Q: How much token savings can I expect?**
A: 40-60% with full implementation. CodeGrok alone = 30-40%. Token optimization strategies = 20-30%.

---

## Reading List

- **Full research:** `docs/research/code-intelligence-tools.md` (15 min read)
- **CodeGrok setup:** https://github.com/dondetir/CodeGrok_mcp (10 min setup)
- **Claude Code token optimization:** https://code.claude.com/docs/en/costs (5 min read)
- **GitHub Projects V2 MCP:** https://github.com/github/github-mcp-server (5 min setup)

---

**Next steps:** Review this summary, then read the full research note before Phase 2 sprint planning.
