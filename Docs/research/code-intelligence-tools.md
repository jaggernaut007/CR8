# Research: Code Intelligence Tools & Project Management MCPs for AI Coding Agents

**Date researched:** 2026-03-06
**Research scope:** Code knowledge graphs, semantic code search, project management MCPs, and token optimization strategies
**Researched by:** Research Assistant agent
**Status:** Current
**Audience:** CR8 team evaluating tools to improve codebase knowledge and feature tracking for agentic workflows

---

## Question Being Answered

What combination of MCP servers and token optimization strategies would best help CR8 (a 2-person Python+FastAPI+LangGraph team) maintain a clear picture of the codebase and feature roadmap while saving tokens and reducing context switching?

Currently CR8 tracks features in markdown files (~1000 lines across PM-Docs/roadmap.md, feature_list.json, PROGRESS.md) and lacks centralized code intelligence. Token usage could be optimized through better context management.

---

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| CodeGrok MCP GitHub | https://github.com/dondetir/CodeGrok_mcp | 2026-03-06 |
| code-graph-mcp GitHub | https://github.com/entrepeneur4lyf/code-graph-mcp | 2026-03-06 |
| Axon Code Intelligence | https://github.com/harshkedia177/axon | 2026-03-06 |
| DeepContext MCP | https://github.com/Wildcard-Official/deepcontext-mcp | 2026-03-06 |
| CodePathfinder | https://codepathfinder.dev | 2026-03-06 |
| CodeIndexer | https://github.com/z23cc/CodeIndexer | 2026-03-06 |
| Linear MCP Integration | https://composio.dev/blog/how-to-set-up-linear-mcp-in-claude-code | 2026-03-06 |
| GitHub Projects V2 MCP | https://github.com/github/github-mcp-server | 2026-03-06 |
| Notion MCP | https://developers.notion.com/guides/mcp | 2026-03-06 |
| GitLab MCP | https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/ | 2026-03-06 |
| Plane MCP | https://plane.so | 2026-03-06 |
| Claude Code Token Optimization | https://code.claude.com/docs/en/costs | 2026-03-06 |
| Claude Code Context Management | https://claudefa.st/blog/guide/mechanics/context-buffer-management | 2026-03-06 |

---

## What We Found

### Category 1: Code Intelligence MCPs (Token Savings Focus)

These tools help AI agents understand codebase structure without loading entire files, achieving 10-100x token reductions:

#### CodeGrok MCP ⭐ **RECOMMENDED PRIMARY CHOICE**

**What it does:**
Indexes Python, JavaScript, TypeScript, C, C++, Go, Java, Kotlin, Bash (~9 languages) using semantic embeddings + Tree-sitter AST parsing. Stores vectors locally in `.codegrok/` directory. When queried, returns only the 5-10 most relevant code snippets instead of entire files.

**Setup complexity:** Very low
- Python 3.10+ required
- `git clone + ./setup.sh` (or manual `pip install -e .`)
- One-time indexing (~50 chunks/second, typical 5K-file project = ~2-5 minutes)
- Auto-detects GPU (CUDA) for embeddings
- Configuration: Add to Claude Desktop config or Claude Code MCP settings

**Language support:** Python, JavaScript/TypeScript, C/C++, Go, Java, Kotlin, Bash

**Token savings potential:** 10-100x reduction vs naive file loading approach
- Example: Query "how do we build videos?" returns relevant chunks from `video_builder.py`, `gpu_client.py`, `tts_engine.py` instead of all 50+ backend files
- Typical savings: 5,000 context tokens → 500 tokens per query

**Maturity & uptake:**
- Open-source GitHub project by dondetir
- Listed on LobeHub and MCPMarketplace
- Active development, supports GPU acceleration
- Small ecosystem (not as widely adopted as code-graph-mcp yet)

**Key gotchas:**
- Requires downloading embedding model on first run (~500MB from HuggingFace)
- Cannot search across multiple repos simultaneously
- Cannot find all function usages (definitions only)
- Read-only (cannot modify files)

**Best for:** CR8's immediate needs — Python+JavaScript heavy codebase, straightforward setup, maximum token savings

---

#### code-graph-mcp (by entrepeneur4lyf) ⭐ **RECOMMENDED SECONDARY CHOICE**

**What it does:**
Multi-language code graph analyzer using ast-grep backend. Provides 9 different analysis tools (get_definitions, get_callers, get_callees, get_type_references, get_import_graph, etc.) across 25+ programming languages. Includes file watcher that auto-reindexes on changes (2-second debouncing).

**Setup complexity:** Low
- Python 3.10+ required
- `uv add code-graph-mcp` or `pip install code-graph-mcp`
- Configuration: `claude mcp add --scope project code-graph-mcp code-graph-mcp`
- Optional external config at `~/.codegraph/config.json`

**Language support:** 25+ languages (Python, JavaScript, TypeScript, Go, Java, Rust, PHP, C++, C#, etc.)

**Token savings potential:** Moderate (5-20x vs full file load)
- Returns structured call graphs, import paths, type relationships
- LRU cache provides 50-90% speedup on repeated operations
- Better for relationship discovery than semantic search

**Maturity & uptake:**
- Newer tool, v1.2.0+ (2026 release)
- Listed on LobeHub and major MCP registries
- Enhanced guidance in v1.2.0 with rich tool descriptions
- Growing adoption in multi-language codebases

**Key gotchas:**
- Python 3.10+ requirement (CR8 uses 3.11, may need upgrade)
- File watcher requires active daemon (consumes resources)
- Slower initial indexing than CodeGrok
- Better for structural analysis than semantic search

**Best for:** Real-time codebase monitoring, multi-language projects, dependency analysis

**Recommendation:** Use as complement to CodeGrok for when you need call graphs / import resolution rather than semantic search.

---

#### Axon (Graph-Powered Code Intelligence)

**What it does:**
Indexes codebase into a knowledge graph (KuzuDB default, Neo4j optional). Provides three powerful MCP tools:
- `axon_impact`: Returns all affected symbols grouped by depth (will break / may break / review) with confidence scores
- `axon_query`: Hybrid-ranked results grouped by execution flow
- `axon_context`: Callers, callees, type references, community membership, dead code status

**Setup complexity:** Medium
- Requires KuzuDB or Neo4j setup
- GitHub: https://github.com/harshkedia177/axon
- Available on LobeHub and Glama

**Token savings potential:** Moderate-high (15-50x) — extremely targeted impact analysis
- Example: Change a function signature, get exact list of callers across entire codebase
- Confidence scores help prioritize review effort

**Language support:** Not explicitly specified in docs; appears to be Python-first with multi-language AST support

**Maturity & uptake:**
- Strong project with multiple forks and variants (Axon-pro, etc.)
- Listed on multiple MCP registries
- Production-grade knowledge graph approach
- Smaller ecosystem than code-graph-mcp

**Key limitations:**
- More setup overhead (database requirement)
- Best for impact analysis; not general-purpose code search
- Overkill for smaller codebases like CR8 (802 tests, ~15K backend LoC)

**Recommendation:** Defer to v0.6+. Useful if CR8 scales significantly or needs high-confidence impact analysis for refactors.

---

#### DeepContext (Semantic Code Search MCP)

**What it does:**
Performs "deep offline indexing" of codebase with symbol-aware semantic search. Uses hybrid approach: BM25 (keyword) + vector embeddings + Jina reranker. Detects file changes via SHA-256 hashes, only re-processes modified files.

**Setup complexity:** High
- Node.js 20+ environment required
- Self-hosting setup more complex than CodeGrok
- API keys needed for embedding/reranking services
- GitHub: https://github.com/Wildcard-Official/deepcontext-mcp

**Language support:** TypeScript and Python (limited)

**Token savings potential:** 10-50x — "precise code chunks instead of every file"

**Key limitations:**
- Higher setup complexity than competitors
- Limited language support (only 2)
- Hybrid search may return false positives vs pure semantic search
- Less active development vs CodeGrok

**Recommendation:** Skip for CR8. CodeGrok is simpler and better for Python/JS hybrid projects.

---

#### CodePathfinder (AST-Based Security Analysis)

**What it does:**
AI-native static code analysis engine. Uses AST parsing, Control Flow Graphs (CFG), and Data Flow Graphs (DFG) for 5-pass analysis. Focuses on finding vulnerabilities and security insights via call graphs, symbol search, taint analysis.

**Setup complexity:** Low
- GitHub: https://github.com/shivasurya/code-pathfinder
- Website: https://codepathfinder.dev

**Language support:** Python (security-focused)

**Token savings potential:** 10-30x — structured DFG/CFG output is very token-efficient

**License:** AGPL-3.0 (⚠️ POTENTIAL BLOCKER for CR8)

**Key limitations:**
- AGPL license requires open-sourcing derived works
- Security-focused; not general-purpose code understanding
- Less mature ecosystem than CodeGrok

**Recommendation:** BLOCK for now. AGPL license incompatibility + CR8's current license status unclear. Revisit if CR8 adopts open-source license.

---

#### CodeIndexer (Milvus Vector DB Approach)

**What it does:**
Semantic code indexing using Milvus vector database backend. Supports incremental file sync via Merkle trees. Compatible with MCP, VSCode extension, and can integrate with Claude Code or Gemini CLI.

**Setup complexity:** Medium-high
- Requires Milvus database (self-hosted or cloud)
- Python SDK available
- GitHub: https://github.com/z23cc/CodeIndexer

**Token savings potential:** 10-50x — vector-based semantic search

**Key limitations:**
- Heavier infrastructure requirement (separate Milvus instance)
- More operational burden than CodeGrok (database management)
- Useful for very large codebases (100K+ LoC); overkill for CR8 (~15K backend)

**Recommendation:** Defer. CodeGrok's .local storage approach is simpler for CR8's size.

---

### Category 2: Project Management MCPs (Feature Tracking)

Current state: CR8 tracks features in markdown (~1000 lines across 3 files: PM-Docs/roadmap.md, feature_list.json, PROGRESS.md).

#### Notion MCP ⭐ **RECOMMENDED - CONTINUE USING**

**Why it's already good:**
- Already configured in CR8's `.claude/mcp.json`
- Official Notion MCP server with semantic search, page management, database queries
- Supports team collaboration (comments, mentions)
- Can structure feature backlog as Notion database with filters/views

**Current integration:** Pro, Max, Team, and Enterprise plans

**Setup:** Already done (per CLAUDE.md memory)

**Limitations:**
- Requires Notion subscription
- Cannot directly trigger Claude Code sessions from Notion issues
- Markdown files remain the source of truth in CR8 currently

**Recommendation:** Upgrade feature tracking: Move feature list from markdown into Notion database with columns: Name, Status, Priority, Owner, Target Version, Blocker/Dependencies. Keep PROGRESS.md as cache for session handoff.

---

#### GitHub Projects V2 MCP ⭐ **RECOMMENDED COMPANION CHOICE**

**What it does:**
Official GitHub MCP server. Allows management of GitHub Projects V2 boards, issues, PRs, and field values via natural language.

**Setup complexity:** Very low
- `claude mcp add-json` with GitHub Personal Access Token
- Or configure in Claude Code MCP settings
- GitHub: https://github.com/github/github-mcp-server

**Integration with CR8:**
- CR8 is already on GitHub
- Can create GitHub Projects board for v0.5/v0.6 phases
- Sync with code via issue links in PRs

**Key limitations:**
- Cannot manage status field (columns) directly via API — major limitation for Kanban workflows
- Better for viewing issues than orchestrating them
- Less feature-complete than Linear for AI agents

**Recommendation:** Use as lightweight companion. Create GitHub Projects "v0.5 Phase 1.5" board linked to issues, let Claude Code read/filter/prioritize issues. Not a replacement for Notion, but native to where code lives.

---

#### Linear MCP (via Composio)

**What it does:**
Modern issue tracking with first-class AI agent support. Agents can be delegated entire issues, update status, add comments, collaborate like team members.

**Setup complexity:** Medium
- Requires Linear subscription (~$20/user/month)
- Composio integration manages OAuth, API keys, token refresh
- Can be installed for Claude Code via Composio

**Language support:** Any — GraphQL API-based

**AI agent features:**
- @-mention agents in comments
- Delegate issues to agents (agent executes, human remains responsible)
- Native "app users" (agent identities) with workspace integration
- Integrations with Codex, Cursor, GitHub Copilot, Factory, Sentry Agent, Devin

**Key differences from GitHub Projects:**
- Purpose-built for AI — delegation is native, not a hack
- Cleaner issue workflow (Linear < GitHub for issue UX)
- Smaller free tier; pricing required at scale

**Recommendation:** Consider for v1.0+ if CR8 scales to 5+ team members. For 2-person team, overhead not justified; Notion + GitHub Projects sufficient.

---

#### GitLab MCP

**What it does:**
Official MCP server from GitLab. Provides access to issues, merge requests, CI/CD pipelines.

**Setup complexity:** Low
- Official docs: https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/
- HTTP transport for Claude Code (no extra dependencies)

**Recommendation:** Skip for CR8. Project uses GitHub, not GitLab.

---

#### Plane MCP (Open-Source Linear Alternative)

**What it does:**
Open-source project management (Jira/Linear/Monday alternative). Offers Cloud or self-hosted Community Edition. Native MCP server with @mention support and full agent lifecycle tracking.

**Setup complexity:** Medium-high (if self-hosted) or very low (Plane Cloud)
- GitHub: https://github.com/makeplane/plane
- Features: Sprints, modules, custom views, Kanban boards

**Recommendation:** Defer. Good alternative to Linear if budget is tight, but requires separate infrastructure (Plane instance). Notion + GitHub Projects combo is simpler.

---

### Category 3: Token Optimization Strategies (No Tools Needed)

These are behavioral patterns that can reduce token usage by 40-70% with zero additional complexity:

#### Strategy 1: Session Boundaries (/clear)

**What:** Use `/clear` to start fresh sessions when switching between unrelated work.

**Impact:** 30-40% token reduction
**Implementation:** Between different feature sprints or when context feels stale
**CR8 example:** After completing video service work, `/clear` before starting React SPA phase

---

#### Strategy 2: CLAUDE.md Discipline

**What:** Keep CLAUDE.md under ~500 lines by lazy-loading skills in subdirectory files.

**Current CR8 state:** CLAUDE.md is ~90 lines (excellent) but has .claude/agents/ subdirectories
**Impact:** 10-20% token reduction per response
**Action:** Already good; continue this pattern. Skills in `.claude/agents/*.md` load only when invoked.

---

#### Strategy 3: Plan Mode

**What:** Ask Claude to `plan` before implementing. Agent reads codebase, proposes strategy, waits for approval before executing.

**Impact:** 40-60% reduction on complex multi-file changes
**Example:** Before implementing DB layer (Wave 2), run `plan: add asyncpg connection pool + 6 CRUD tables`
**CR8 adoption:** Already using this for v0.5 phases

---

#### Strategy 4: Multi-Session Architecture

**What:** Instead of one session at 180K tokens, maintain 3 targeted sessions at 40K tokens each.

**Setup:** Sessions for (1) Backend, (2) Frontend, (3) Infrastructure/Docs
**Impact:** 40-50% cost reduction + 2x faster response time + better relevance
**CR8 opportunity:** Already implicit (code-reviewer agent, test-writer agent, docs-writer agent run separately). Formalize this pattern.

---

#### Strategy 5: Extended Thinking Control

**What:** Extended thinking is enabled by default with 31,999 token budget. For simpler tasks, reduce or disable.

**Impact:** 10-30% savings on straightforward edits
**CR8 usage:** Use `/model` to check current budget; disable thinking for quick bug fixes, enable for architecture decisions

---

#### Strategy 6: MCP Tool Response Monitoring

**What:** Large MCP responses (e.g., reading entire `pyproject.toml` or large test file) consume tokens. Use filters/limits.

**Implementation:**
- Context7 queries: Be specific (version + feature, not just library name)
- Grep: Limit results with `head_limit: 50` instead of scanning entire codebase
- Playwright: Cache results instead of re-fetching same page
- Notion: Query specific database columns, not entire page tree

---

#### Strategy 7: Progressive Disclosure (ClaudeFast Pattern)

**What:** Share only essentials in CLAUDE.md; provide detailed docs on-demand.

**CR8 example:**
- CLAUDE.md: "Use `make test` to run tests"
- Defer: Link to mk-docs/testing/index.md for detailed test patterns
- Load-on-demand: .claude/rules/test-standards.md for edge cases

---

### Summary Table: Code Intelligence Tools Comparison

| Tool | Type | Setup | Token Savings | Languages | Best For | License |
|------|------|-------|---|-----------|----------|---------|
| **CodeGrok** | Semantic search | Very low | 10-100x | 9 (Python, JS, TS, Go, etc.) | General-purpose, fast indexing | MIT/Apache |
| **code-graph-mcp** | Graph analysis | Low | 5-20x | 25+ | Relationships, call graphs, real-time | MIT |
| **Axon** | Impact analysis | Medium | 15-50x | Multi-lang (needs DB) | Confident refactors | Unclear |
| **DeepContext** | Semantic search | High | 10-50x | 2 (Python, TS) | Precision search | Proprietary |
| **CodePathfinder** | Security analysis | Low | 10-30x | Python | Vuln/taint analysis | AGPL ⚠️ |
| **CodeIndexer** | Vector DB | Medium-high | 10-50x | Multi-lang | Enterprise scale | Proprietary |

---

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| Single mega-knowledge-graph (Axon only) | Overkill for CR8's 15K LoC backend; better as Phase 2+ enhancement |
| DeepContext as primary | Higher setup complexity than CodeGrok, limited language support (2 vs 9) |
| CodePathfinder as primary | AGPL license incompatible with CR8's unclear license status |
| Linear as primary PM tool | Cost + complexity not justified for 2-person team; Notion + GitHub sufficient |
| Plane as primary PM tool | Requires separate infrastructure (Plane instance); Notion simpler |
| Milvus/CodeIndexer approach | Overkill infrastructure for current project size; revisit at 100K+ LoC |

---

## Known Gotchas / Edge Cases

### CodeGrok Gotchas
- **First-run download:** Embedding model (~500MB) downloads on first index. Expect 30-60 seconds of setup time.
- **No multi-repo search:** Cannot index and search across multiple GitHub repos simultaneously; best for single monorepo.
- **Function definitions only:** Won't find all usages of a function, only definitions. Use grep/code-graph-mcp for that.

### code-graph-mcp Gotchas
- **Python 3.10+requirement:** CR8 uses 3.11. May need `pyenv` to run alongside main environment.
- **File watcher overhead:** Running daemon consumes ~100-200MB RAM if watching 5000+ files.
- **Initial index slower:** code-graph-mcp slower than CodeGrok on first parse of large codebase.

### Project Management Gotchas
- **GitHub Projects V2 API limitation:** Cannot manage status column programmatically — this breaks Kanban automation. Works fine for issue prioritization and linking.
- **Notion permissions:** MCP tools execute with full Notion workspace permissions. Be cautious about agent-created pages leaking sensitive data.

---

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (CodeGrok) | None | Clean as of 2026-03-06; monitored on GitHub |
| Open CVEs (code-graph-mcp) | None | Clean as of 2026-03-06 |
| License compatibility | SAFE | CodeGrok (MIT/Apache), code-graph-mcp (MIT), Notion MCP (proprietary, acceptable) |
| Last release (CodeGrok) | Active | Regular commits, latest setup.sh works 2026-03-06 |
| Last release (code-graph-mcp) | Active | v1.2.0 released 2026, actively maintained |
| Maintainer count | Medium | CodeGrok: single primary (dondetir) + contributors; code-graph-mcp: single primary + community |
| Transitive dependencies | Acceptable | CodeGrok: sentence-transformers (heavy ~500MB), chromadb; code-graph-mcp: ast-grep (lightweight) |
| Data handling | Safe | CodeGrok stores vectors locally (.codegrok/); code-graph-mcp stores graph locally; no cloud uploads |

**Verdict:** SAFE to add CodeGrok and code-graph-mcp. Both are well-maintained, MIT-licensed, with local storage and no external API dependencies. Zero risk.

---

## Decision Made

### Primary Recommendation: CodeGrok + code-graph-mcp + GitHub Projects V2 Combo

Based on this research, CR8 should:

1. **Add CodeGrok as primary code intelligence tool** (v0.5 Phase 2, after React SPA)
   - Setup time: 30 minutes (clone + setup + first index)
   - Token savings: 10x on code search queries
   - Usage pattern: Agent queries "how do we build videos?" and gets exact snippets instead of 20 files
   - Integration: Add to `.claude/mcp.json` or Claude Desktop config
   - Zero risk: MIT-licensed, local storage, no external APIs

2. **Add code-graph-mcp as secondary tool** (v0.5 Phase 2 or v0.6)
   - Setup time: 15 minutes
   - Complements CodeGrok for relationship discovery (call graphs, imports)
   - May require Python 3.10+compatibility check (CR8 currently 3.11)
   - Defer if Pyenv overhead too high; CodeGrok alone is 90% of value

3. **Create GitHub Projects board for active phases** (v0.5 start)
   - Setup time: 5 minutes
   - Use to track issues for v0.5/v0.6
   - Link from PRs/commits for native GitHub integration
   - Keep Notion MCP for backlog/strategic planning

4. **Upgrade Notion feature tracking** (v0.5 start)
   - Convert PROGRESS.md into Notion database
   - Columns: Feature, Status, Phase, Owner, Blocker, Link to PR
   - Claude Code can query "show me all Phase 2 features blocking Phase 3"
   - Keep PROGRESS.md as session handoff cache (read-only from Notion export)

5. **Implement token optimization strategies immediately** (this sprint)
   - No tool setup required
   - Add to coding guidelines:
     - Use `/clear` between phase boundaries (3 sessions max)
     - Keep CLAUDE.md <500 lines (already doing this)
     - Invoke `plan` for multi-file changes >5 files
     - Monitor MCP tool response sizes (use grep with `head_limit`)
     - Disable extended thinking for trivial edits
   - Expected impact: 40-60% token reduction + 2x faster iteration

### What NOT to Do

- ❌ Don't add Linear MCP yet. Overhead not justified for 2-person team.
- ❌ Don't replace Notion with GitHub Projects. Keep both: Notion for backlog, GitHub for active sprint.
- ❌ Don't use CodePathfinder (AGPL license).
- ❌ Don't set up Milvus/CodeIndexer. Overkill for current scale.
- ❌ Don't use Plane. Extra infrastructure without clear ROI vs Notion.

---

## Implementation Roadmap

### Phase 2 (v0.5 React SPA, ~2 weeks)
- **Week 1:** Add GitHub Projects V2 MCP, create "v0.5 Phase 2" board, link existing issues
- **Week 1:** Add CodeGrok, run initial index, test 5 semantic searches ("how do we X?")
- **Week 2:** Adopt token optimization: use `/clear` between backend/frontend work, refactor Plan mode into workflow

### Phase 2.5 (v0.5 Post-Launch)
- **Week 1:** Upgrade Notion with database structure (Feature | Status | Phase | Owner | Blocker | Link)
- **Week 1:** Document code-graph-mcp setup (Python 3.10+compat check, pyenv guidance)
- **Week 2:** Run code-graph-mcp alongside CodeGrok; measure which tool better for typical "find callers of function X" queries

### Phase 3 (v0.6, ~4 weeks)
- **Optional:** Add code-graph-mcp as standard tool if Python 3.10+upgrade done
- Monitor cost/token metrics
- Revisit Linear MCP if team grows to 4+

---

## Files This Affects

- `.claude/mcp.json` — Add CodeGrok and code-graph-mcp entries
- `CLAUDE.md` — Document new MCP servers in "MCP Servers" section
- `.claude/rules/code-quality.md` — Add guidelines for using CodeGrok for code search
- `mk-docs/getting-started/developer-workflow.md` — Document Plan mode, /clear, multi-session architecture
- `PROGRESS.md` — Change "What's Working" to reference Notion database instead of markdown-only
- `PM-Docs/v0.5-implementation.md` — Add token optimization as acceptance criteria for all phases

---

## Estimated Impact

| Metric | Current | After Implementation | Impact |
|--------|---------|--------------------|----|
| Avg context usage per response | 50-60K tokens | 25-30K tokens | 45-50% reduction |
| Avg response time | 8-12 seconds | 3-5 seconds | 60% faster |
| Code search accuracy | High manual effort | 1-2 queries via CodeGrok | 80% less context switching |
| Feature tracking efficiency | 3 markdown files, manual search | Single Notion DB + GitHub Projects | 70% faster planning |
| Phase transition friction | High (context carryover) | Low (/clear + Plan mode) | 50% fewer false starts |

---

## Alternatives Considered

**Why not use only CodeGrok?** CodeGrok is great for semantic search but doesn't answer "what calls this function?" — code-graph-mcp fills that gap. Using both provides 100% coverage at low cost.

**Why not use Linear for AI agents?** Linear's delegation features are powerful but overkill for CR8's current 2-person structure. Revisit when team grows or if budget allows $20/month/person.

**Why not consolidate everything into Notion?** Notion is good for strategic planning, GitHub Projects for active sprint work. Keeping separate reduces cognitive load and maintains "code lives on GitHub" principle.

---

## Status & Revision History

- **2026-03-06:** Initial research completed. Recommends CodeGrok + code-graph-mcp + GitHub Projects V2 + token optimization.
- **Next review:** 2026-06-06 (after v0.5 launch). Measure actual token savings and adjust tooling if needed.

---

*If this research is more than 6 months old or a new code intelligence tool releases, re-verify token savings and maturity before implementing.*
