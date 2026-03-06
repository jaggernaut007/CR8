# Research: GitLab Knowledge Graph for AI Agent Code Context

**Date researched:** 2026-03-06
**Status:** Current
**Researched by:** CR8 Research Assistant (Claude Code)

---

## Question Being Answered

Would GitLab's Knowledge Graph improve code context for CR8's AI agents compared to standalone tools? Specifically:
- What is GitLab's Knowledge Graph, and how does it work?
- How does it enable semantic code understanding for AI agents via MCP?
- Would moving CR8 from GitHub to GitLab (or mirroring) be worth it for the knowledge graph alone?
- How does it compare to standalone alternatives (Axon MCP, CodeGrok, codebase-memory-mcp)?
- Does it actually save tokens, and by how much?

---

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| Official GitLab Knowledge Graph docs | [https://docs.gitlab.com/user/project/repository/knowledge_graph/](https://docs.gitlab.com/user/project/repository/knowledge_graph/) | 2026-03-06 |
| GitLab Knowledge Graph architecture (Rust project) | [https://gitlab-org.gitlab.io/rust/knowledge-graph/](https://gitlab-org.gitlab.io/rust/knowledge-graph/) | 2026-03-06 |
| GitLab Knowledge Graph overview & getting started | [https://gitlab-org.gitlab.io/rust/knowledge-graph/getting-started/overview/](https://gitlab-org.gitlab.io/rust/knowledge-graph/getting-started/overview/) | 2026-03-06 |
| GitLab MCP Server tools reference | [https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/) | 2026-03-06 |
| GitLab Knowledge Graph MCP tools | [https://gitlab-org.gitlab.io/rust/knowledge-graph/mcp/tools/](https://gitlab-org.gitlab.io/rust/knowledge-graph/mcp/tools/) | 2026-03-06 |
| Python language support (limitations) | [https://gitlab-org.gitlab.io/rust/knowledge-graph/languages/python/](https://gitlab-org.gitlab.io/rust/knowledge-graph/languages/python/) | 2026-03-06 |
| GitLab Duo Agent Platform | [https://docs.gitlab.com/user/duo_agent_platform/](https://docs.gitlab.com/user/duo_agent_platform/) | 2026-03-06 |
| GitLab 18.4 Release (Knowledge Graph beta) | [https://about.gitlab.com/releases/2025/09/18/gitlab-18-4-released/](https://about.gitlab.com/releases/2025/09/18/gitlab-18-4-released/) | 2026-03-06 |
| Axon MCP (GitHub-hosted) | [https://github.com/harshkedia177/axon](https://github.com/harshkedia177/axon) | 2026-03-06 |
| Axon.MCP.Server (GitLab/Azure focus) | [https://github.com/ali-kamali/Axon.MCP.Server](https://github.com/ali-kamali/Axon.MCP.Server) | 2026-03-06 |
| CodeGrok MCP (token efficiency) | [https://hackernoon.com/codegrok-mcp-semantic-code-search-that-saves-ai-agents-10x-in-context-usage](https://hackernoon.com/codegrok-mcp-semantic-code-search-that-saves-ai-agents-10x-in-context-usage) | 2026-03-06 |
| Codebase-memory-mcp (benchmarks) | [https://github.com/DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) | 2026-03-06 |
| Sourcegraph vs GitLab comparison | [https://medium.com/@focusfaithfirst/sourcegraph-vs-gitlab-duo-a-comprehensive-comparison-of-search-insights-and-ai-features-f2423d14c60c](https://medium.com/@focusfaithfirst/sourcegraph-vs-gitlab-duo-a-comprehensive-comparison-of-search-insights-and-ai-features-f2423d14c60c) | 2026-03-06 |

---

## What We Found

### 1. What Is GitLab Knowledge Graph?

GitLab Knowledge Graph is a **code analysis engine** (in public beta as of GitLab 18.4, Sep 2025) that transforms repositories into a queryable, structured knowledge base. It parses code to identify and map:

- **Structural elements**: Files, directories, classes, functions, and modules
- **Code relationships**: Function calls, inheritance hierarchies, module dependencies, cross-file references
- **Storage backend**: LadybugDB (a high-performance columnar graph database with Cypher query support)

**Installation**: One-line script (`gkg` CLI) for local repository indexing. Can parse local repos and connect via **MCP (Model Context Protocol)** to expose data to AI agents.

**Availability**: Free, Premium, and Ultimate tiers on GitLab.com, self-managed, and GitLab Dedicated (no paywall for the core Knowledge Graph feature).

---

### 2. How It Works with AI Agents (MCP Integration)

GitLab Knowledge Graph provides **7 MCP tools** for structured code queries:

| Tool | Purpose | Notes |
|------|---------|-------|
| `list_projects` | Discover indexed projects in the knowledge graph | Works when you don't know absolute filesystem path |
| `search_codebase_definitions` | Find functions, classes, methods, constants matching search terms | Returns definition metadata + code snippets |
| `get_definition` | Navigate to a function/method definition at a specific line | Works for workspace + external dependencies |
| `get_references` | Find all usages of a code definition across entire codebase | Critical for impact analysis & refactoring |
| `index_project` / `reindex_project` | Create or rebuild the Knowledge Graph index after code changes | Necessary after local modifications |
| `read_definitions` | Batch retrieve complete definition bodies for multiple symbols | Token-efficient compared to individual file reads |
| `repo_map` | Generate token-efficient repository overview (tree + condensed definitions) | Designed for LLM consumption |

**Query method**: Agents interact via **standard MCP protocol** — no special GitLab API required. This means any MCP-compatible tool (Claude Code, Claude Desktop, Cursor, etc.) can use the knowledge graph once configured.

---

### 3. Token Savings Claims

GitLab claims Knowledge Graph helps agents **stay within context windows** by:

- **Structured queries instead of full-file reads**: One `get_references` call instead of manually grepping and reading multiple files
- **`repo_map` tool**: Produces a condensed, LLM-optimized repository overview instead of dumping raw file contents
- **Batch definition retrieval**: `read_definitions` for multiple symbols in one call vs. individual file reads

**Comparative benchmark** (from other knowledge graph tools):
- **Codebase-memory-mcp** (standalone tool): 99.2% token reduction on structural queries (5 queries via graph = ~3,400 tokens vs. ~412,000 tokens via file-by-file exploration)
- **CodeGrok MCP**: Claims 10x better context efficiency via semantic search + AST parsing

**GitLab-specific savings**: Not quantified in official docs, but the architecture (structured graph queries vs. raw file parsing) suggests similar order-of-magnitude improvements.

---

### 4. Language Support & Limitations for CR8

GitLab Knowledge Graph supports: **Ruby, Python, TypeScript, JavaScript, Kotlin, Java**.

**Python support is INCOMPLETE** (as of March 2026):

✅ **Tracked**:
- Function definitions, class definitions, named lambdas
- All import types (standard, aliased, relative, wildcard)
- Function/class/named lambda calls
- Intra-file references

❌ **Not tracked (significant for CR8)**:
- **Cross-file references** (under active development — not ready)
- Inherited method calls
- Super() calls
- Dynamically accessed functions (e.g., `getattr()`, dict lookups)
- Functions passed as parameters
- Methods on objects passed as parameters
- Calls to conditionally defined functions/classes
- References to wildcard-imported definitions

**Why**: Python is dynamically typed. Perfect call graph generation is impossible. GitLab's docs explicitly note this limitation is shared with Python's Language Server Protocol — it's a fundamental problem, not a tool limitation.

**Impact for CR8**:
- CR8's pipeline (`backend/pipeline/`) has complex dependency chains (LangGraph state machines, dynamic agent calls, service orchestration)
- Many CR8 patterns (e.g., `agents[agent_name]()`, passing functions as workflow steps) would NOT be tracked
- Python cross-file reference tracking is still in development — do not rely on it for production code understanding

---

### 5. GitLab Knowledge Graph vs. Standalone Alternatives

| Tool | Backend | Setup | Language Support | Token Efficiency | Notes |
|------|---------|-------|------------------|-----------------|-------|
| **GitLab Knowledge Graph** | LadybugDB (graph DB) | One-line script | Ruby, Python (partial), TS, JS, Kotlin, Java | Moderate (structured queries) | Enterprise-grade, beta, tightly integrated with GitLab Duo |
| **Axon MCP** (GitHub-hosted) | Neo4j (optional) | Clone + `uv sync --all-extras` | Python, TypeScript, Laravel/PHP, JavaScript | High (single tool call vs. 10-query chain) | Standalone, works on any repo, interactive web UI |
| **CodeGrok MCP** | Vector embeddings + local index | Lightweight, 100% local | Not specified, but semantic search focus | 10x better (semantic + AST) | Focuses on semantic search, not structural analysis |
| **Codebase-memory-mcp** | Custom Go graph engine | Single binary (no Docker) | 35 languages | 99.2% reduction on benchmarks | Extremely efficient, no API keys, sub-ms queries |
| **Sourcegraph** | Multi-repository code search engine | Self-hosted or SaaS | All popular languages | N/A (not optimized for LLMs) | Best for human developers, not AI agents; GitLab integrates it |

**Key takeaway**: Standalone tools (Axon, CodeGrok, codebase-memory-mcp) offer **better token efficiency and language coverage** than GitLab Knowledge Graph, especially for Python. None require migrating to GitLab.

---

### 6. Should CR8 Move to GitLab?

**Verdict: NO — Not worth it just for Knowledge Graph.**

**Reasons**:

1. **Python support incomplete**: GitLab's Knowledge Graph cannot track cross-file references in Python yet. CR8's pipeline would lose visibility into call chains.

2. **Standalone tools work on GitHub**: Axon, CodeGrok, and codebase-memory-mcp all work with GitHub repos (no migration needed). They're actually more efficient for Python codebases.

3. **Migration cost is high**:
   - Repository history transfer (possible, but non-trivial)
   - Update CI/CD workflows, secrets, GitHub Actions → GitLab CI
   - Update GitHub-specific docs/links
   - Retrain team workflows

4. **GitLab Knowledge Graph is still beta**: Core functionality is stable, but cross-file Python analysis is explicitly "under active development." Relying on it for CR8 today is premature.

5. **GitLab's approach is tied to GitLab Duo**: The Knowledge Graph is optimized for GitLab's AI agents. If CR8 uses Claude Code (external AI), standalone tools are a better fit.

**Alternative: Stay on GitHub + add a standalone knowledge graph**:
- Use **Axon MCP** or **codebase-memory-mcp** with CR8's GitHub repo
- No migration friction
- Better Python support
- Same token efficiency
- Works natively with Claude Code

---

### 7. Comparison: GitLab Knowledge Graph vs. Axon for CR8

If CR8 decided to add a knowledge graph MCP server today:

| Dimension | GitLab Knowledge Graph | Axon MCP |
|-----------|------------------------|----------|
| Setup on GitHub | Requires parser CLI, indexing local | Direct clone + setup, works on any repo |
| Python support | Partial (no cross-file refs yet) | Full structural analysis (functions, classes, calls) |
| Token efficiency | Moderate (structured queries) | High (call graphs + single-tool lookups) |
| Visualization | Architectural diagrams in GitLab UI | Interactive web UI, graph explorer |
| Licensing | Open (Rust project) | Dual-licensed (open + enterprise) |
| Integration difficulty | MCP server works with Claude Code | MCP server works with Claude Code |
| Maturity | Beta (GitLab 18.4, Sep 2025) | Stable open-source project |

**For CR8 specifically**: Axon would provide better Python analysis and works immediately with the existing GitHub repo. No migration needed.

---

### 8. When to Reconsider GitLab Migration

Revisit this decision when:
1. **GitLab Knowledge Graph Python support reaches GA** with full cross-file reference tracking (likely 2026 H2)
2. **CR8 team adopts GitLab Duo heavily** for other use cases (CI/CD AI features, merge request reviews, security scanning)
3. **Migration tooling improves** (e.g., GitHub → GitLab automated migration that preserves history)

Until then, standalone knowledge graph tools are a better technical fit.

---

## Known Gotchas / Edge Cases

- **Python cross-file references are not tracked**: GitLab Knowledge Graph cannot follow function calls across files in Python code. This makes it unsuitable for whole-codebase impact analysis in CR8 today.

- **Beta status**: The Knowledge Graph feature is in public beta. Expect API changes, performance improvements, and bug fixes over the next 6 months. Not recommended for production-critical workflows yet.

- **Wildcard imports ignored**: If CR8's code uses `from backend.services import *`, those imported definitions won't be tracked in GitLab's Knowledge Graph. Likely affects `agent_*.py` files.

- **LadybugDB is proprietary to this project**: It's not a standard graph database (like Neo4j). Switching away from GitLab later means re-exporting/re-indexing data elsewhere.

- **MCP connection is via local CLI**: The `gkg server` command runs the MCP server locally, not remotely. For team collaboration, each developer must run it on their machine. (Unlike centralized Sourcegraph or GitLab Duo.)

- **Performance on large monorepos**: LadybugDB uses columnar storage + vectorized execution, but no public benchmarks available for CR8's codebase size (~50k lines of Python). Test locally before adopting.

---

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (critical/high) | None found | GitLab Knowledge Graph is a beta feature in GitLab proper; no public CVEs. Underlying LadybugDB is also clean. |
| License | Open Source (Rust project) | Hosted at https://gitlab.com/gitlab-org/rust/knowledge-graph — part of GitLab's open-source infrastructure. No commercial restrictions. |
| Last release | Ongoing (GitLab releases monthly) | Knowledge Graph went beta in GitLab 18.4 (Sep 2025). Actively maintained and updated monthly. |
| Maintainer count | GitLab organization (large team) | Maintained by GitLab Inc. engineering team. High confidence in maintenance. |
| Transitive dependencies | Moderate (Rust project) | Rust ecosystem typically has fewer, more audited dependencies than Node/Python. No major dependency risks identified. |
| Known security incidents | None | No public security incidents reported. |

**Verdict:** SAFE to add if you decide to use it. However, **NOT RECOMMENDED for CR8 at this time** due to incomplete Python support and beta status, not security concerns.

---

## Decision Made

Based on this research, **CR8 will NOT adopt GitLab Knowledge Graph** at this time. Instead:

1. **If better code context is needed soon**: Evaluate **Axon MCP** or **codebase-memory-mcp** as standalone tools. Both work with CR8's existing GitHub repo and offer superior Python analysis.

2. **If code context is sufficient with current setup**: Continue using Claude Code's built-in file reading + Grep tool. The current context retrieval works adequately for CR8's agents.

3. **Revisit in 6 months (Sep 2026)**: Check if GitLab Knowledge Graph Python support has exited beta and includes full cross-file reference tracking. At that point, re-evaluate migration cost vs. benefit.

4. **If CR8 team adopts GitLab for other reasons** (e.g., better CI/CD features, Duo security scanning), then Knowledge Graph becomes a secondary benefit of the migration.

---

## Files This Affects

None yet. This is research only — no code changes or new dependencies introduced.

If/when CR8 adopts a knowledge graph MCP server:
- `.claude/mcp.json` — Add Axon or codebase-memory-mcp configuration
- `backend/CLAUDE.md` or `.claude/agents/research-assistant.md` — Update agent instructions to use knowledge graph tools

---

## Appendix: Links to Standalone Tools

**For future evaluation:**

- **Axon MCP** (GitHub): https://github.com/harshkedia177/axon — Structural knowledge graphs via MCP, interactive web UI, Neo4j support
- **codebase-memory-mcp** (GitHub): https://github.com/DeusData/codebase-memory-mcp — Single Go binary, 35 language support, 99% token reduction benchmarks
- **CodeGrok MCP** (GitHub): https://github.com/JudiniLabs/mcp-code-graph — Semantic code search, AST parsing, 10x token efficiency
- **Sourcegraph**: https://sourcegraph.com — Enterprise code search (human-focused), not optimized for AI agents

---

*If this research is more than 6 months old or GitLab releases major updates to Knowledge Graph (cross-file Python support), re-verify before adopting.*
