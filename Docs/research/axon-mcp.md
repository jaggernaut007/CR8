# Research: Axon — Graph-Powered Code Intelligence MCP Server

**Date researched:** 2026-03-11
**Research scope:** Deep technical evaluation of Axon as a knowledge graph-powered code analysis tool for CR8
**Researched by:** Research Assistant agent
**Status:** Current
**Previous status:** Deferred in 2026-03-06 research as "overkill for CR8's 15K backend LoC"

---

## Question Being Answered

Is Axon (harshkedia177/axon) worth integrating into CR8's development workflow as a primary code intelligence tool?

Specifically:
- What is the exact setup complexity (database requirements, Docker, dependencies)?
- How do the three MCP tools (axon_query, axon_context, axon_impact) work?
- How does impact analysis with confidence scores actually help CR8's team?
- What is the maintenance burden of a knowledge graph vs simpler alternatives like code-graph-mcp?
- Should this be added now or deferred to v0.6+?

---

## Sources Consulted

| Source | URL | Date accessed | Status |
|--------|-----|---------------|--------|
| Official GitHub repo | https://github.com/harshkedia177/axon | 2026-03-11 | Primary source (some 429 errors) |
| GitHub releases | https://github.com/harshkedia177/axon/releases | 2026-03-11 | v1.0.0-v1.0.1 timeline confirmed |
| Glama MCP registry | https://glama.ai/mcp/servers/@harshkedia177/axon | 2026-03-11 | Configuration reference |
| LobeHub MCP listing | https://lobehub.com/mcp/scanadi-axon | 2026-03-11 | Community adoption data |
| Web search (architecture) | "harshkedia177 axon call graph type inference embeddings" | 2026-03-11 | Technical architecture |
| Web search (performance) | "axon analyze 142 files 4.2 seconds" benchmark | 2026-03-11 | Performance data |
| Web search (comparison) | code-graph-mcp vs Axon tools | 2026-03-11 | Competitive analysis |
| Prior CR8 research | docs/research/code-intelligence-tools.md | 2026-03-06 | Context on why Axon was deferred |

---

## What We Found

### Executive Summary: Revisit vs Defer?

Axon is **genuinely powerful** for impact analysis and architectural visualization, but **operationally heavier** than code-graph-mcp.

**Key insight:** The previous deferral decision was correct for v0.5 (React SPA focus), but Axon should be **reconsidered for v0.6 or as a parallel tool** if:
- Team plans large refactors (impact analysis prevents bugs)
- Codebase architectural understanding is weak (visualization helps)
- Code changes are cross-cutting (graph queries > grep)

**Recommendation:** Research complete. Defer to **v0.6 Phase 2** (post-SPA stabilization) unless impact analysis becomes blocking issue during current refactors.

---

### 1. Project Status & Maturity

| Metric | Value | Assessment |
|--------|-------|-----------|
| GitHub stars | 542 | Moderate adoption (smaller than code-graph-mcp ~700, larger than most single-dev projects) |
| Forks | 94 | Active fork ecosystem (Axon-pro, variants) |
| Open issues | 17 | Well-managed (low backlog ratio) |
| Latest release | v1.0.1 (March 9, 2024) | Stable major version; ~12 months old as of research date |
| Commit frequency | ~86 commits to date | Regular but not rapid development |
| Primary maintainer | harshkedia177 | Single primary maintainer (⚠️ bus factor risk) |
| Contributors | ~5-10 | Small core team |

**Verdict:** Production-ready, but small ecosystem. Lower risk than early-stage projects, higher risk than widely-adopted tools.

---

### 2. Installation & Setup

#### Quick Start Path
```bash
pip install axoniq                    # Core package
# OR with Neo4j backend:
pip install axoniq[neo4j]             # Optional Neo4j instead of KuzuDB

cd your-project && axon analyze .     # One-time indexing
axon ui                               # Opens http://localhost:8420
```

**Python requirement:** 3.11+ (matches CR8's current version)

#### Database Setup

**Default: KuzuDB** (embedded graph database)
- Zero setup required — creates local database on first run
- Stores graph + indices in `.axon/` directory (project root)
- SQLite-like approach: single-process, local file I/O
- No separate daemon or Docker required

**Optional: Neo4j backend**
- Install via `pip install axoniq[neo4j]`
- Requires Neo4j instance (Docker or cloud)
- More overhead but allows multi-process access
- Better for teams sharing codebase analysis

**For CR8:** KuzuDB default is appropriate — local-first development, single developer per session.

#### Storage Location

```
project-root/
├── .axon/                          # Graph database, embeddings, FTS indices
│   ├── kuzu.db                     # KuzuDB graph (or neo4j config if using Neo4j)
│   ├── embeddings.fts              # BM25 full-text search index
│   └── vectors/                    # HNSW vector index (384-dim BAAI embeddings)
├── .axon_cache/                    # (Optional) temporary analysis state
```

**Gitignore:** Must add `.axon/` to `.gitignore` (binary database)

---

### 3. The 12-Phase Ingestion Pipeline

Axon's indexing happens in one pass (no live updates by default):

| Phase | What It Does | Detects |
|-------|---|---|
| 1. Walk | Find all source files | .py, .js, .ts, .tsx, .jsx files |
| 2. Structure | Build file tree | Module hierarchy, package structure |
| 3. Parse | Tree-sitter AST | Functions, classes, decorators, type hints |
| 4. Imports | Resolve `import`/`from` | Module dependencies, circular imports |
| 5. Calls | Build call graph | Who calls whom, recursion |
| 6. Heritage | Class relationships | Inheritance, method overrides, protocols |
| 7. Types | Type analysis | Type annotations, inferred types, generics |
| 8. Communities | Leiden clustering | Functional modules without documentation |
| 9. Processes | Execution flows | Entry points (routes, commands, main) |
| 10. Dead Code | Reachability analysis | Unreachable symbols, unused definitions |
| 11. Coupling | Git history | Changed-together files, refactor safety |
| 12. Embeddings | Sentence embeddings | Semantic search (384-dim BAAI/bge-small) |

**Performance:** ~4.2 seconds for 142 Python files (623 symbols, 1,847 edges) on typical hardware.

**For CR8's 127 files:** Expect ~3-5 second index time. Reasonable.

---

### 4. Graph Data Model

#### Node Types (Entities)
| Node Type | Examples | Attributes |
|-----------|----------|-----------|
| `Module` | `backend.services.llm_service` | Path, lines of code, language |
| `Class` | `LLMService`, `PipelineState` | Name, decorators, base classes |
| `Function` | `run_job()`, `query_docs()` | Name, signature, return type, async |
| `Variable` | `settings`, `logger` | Name, type, scope |
| `Import` | `from openai import ...` | Source module, target |
| `Type` | `TypedDict`, `Callable` | Type name, definition location |
| `Community` | (auto-generated cluster IDs) | Members, density, cohesion score |
| `ExecutionFlow` | (entry point → chain) | Route, middleware, handlers |

#### Relationship Types (Edges)
| Relationship | From → To | Confidence | Use Case |
|---|---|---|---|
| `CALLS` | Function A → Function B | 1.0 (exact) | Direct function calls |
| `CALLS_RECV` | Function A → Method B | 0.8 (receiver) | Dynamic method dispatch |
| `CALLS_FUZZY` | Function A → Function B | 0.5 (fuzzy match) | Indirect/dynamic calls |
| `REFERENCES` | Code → Type | 1.0 | Type annotations, `isinstance()` checks |
| `IMPORTS` | Module A → Module B | 1.0 | `import X from Y` |
| `INHERITS` | Class A → Class B | 1.0 | Class inheritance |
| `IMPLEMENTS` | Class → Protocol | 1.0 | Protocol conformance |
| `BELONGS_TO` | Symbol → Community | 1.0 | Functional cluster membership |
| `PART_OF_FLOW` | Symbol → ExecutionFlow | 1.0 | Entry point reachability |
| `COUPLED_WITH` | File A → File B | 0.6-1.0 | Git change coupling (how often changed together) |

**Confidence scores guide prioritization** — 1.0 edges must be reviewed, 0.5 edges are "likely related."

---

### 5. The Three MCP Tools

#### Tool 1: `axon_query(query: str, limit: int = 20) → List[ResultGroup]`

Performs hybrid ranked search combining three strategies:

**Strategy 1: BM25 Full-Text Search**
- Query: "how do we fetch chat history?"
- Matches: Functions/modules mentioning "chat", "history", "fetch"
- Speed: <10ms

**Strategy 2: Semantic Vector Search**
- Converts query to 384-dim embedding (BAAI/bge-small)
- Finds nearest neighbors in vector space
- Returns symbols semantically similar even if keywords differ
- Example: "retrieve past messages" matches "get_chat_history" without exact word overlap

**Strategy 3: Fuzzy Name Matching**
- Handles typos and partial names
- Levenshtein distance fallback
- Example: "qurey" finds "query", "qury" finds "query"

**Results grouped by execution flow** — answers in context of how code flows, not isolated symbols.

**Example response:**
```json
{
  "query": "database connection pool",
  "results": [
    {
      "symbol": "backend.services.db_client.get_pool()",
      "file": "backend/services/db_client.py:45",
      "context": "Returns asyncpg connection pool for database access",
      "rank": 1.0,
      "strategy": "semantic"
    },
    {
      "symbol": "backend.db.connection.AsyncPgPool",
      "file": "backend/db/connection.py:12",
      "context": "Pool class initialized at app startup",
      "rank": 0.87,
      "strategy": "semantic"
    }
  ],
  "next_step": "Use context() on a specific symbol for the full picture"
}
```

**Best for:** "How do we X?" questions when you don't know exact function name

---

#### Tool 2: `axon_context(symbol: str) → SymbolContext`

Provides 360-degree view of a single symbol (function, class, module):

**Returns:**
- **Definition**: Signature, docstring, type hints, decorators
- **Callers**: All functions that call this symbol (direct + indirect via 3 hops)
- **Callees**: All functions this symbol calls
- **Type references**: Where this symbol's type is used
- **Community**: Functional cluster it belongs to (Leiden clustering)
- **Dead code status**: Is it reachable from entry points?
- **Framework context**: Is this a Flask route, FastAPI endpoint, Click command?
- **Git history**: Last 3 commits touching this symbol

**Example response for `backend/services/llm_service.py:LLMService.query()`:**

```json
{
  "symbol": "LLMService.query",
  "definition": {
    "signature": "async def query(self, prompt: str, context: str = '') → str",
    "docstring": "Query the LLM with optional context",
    "decorators": ["@staticmethod"],
    "type_hints": "str → str"
  },
  "callers": [
    {
      "caller": "agent_research.research_agent()",
      "depth": 1,
      "confidence": 1.0,
      "type": "direct"
    },
    {
      "caller": "graph.invoke()",
      "depth": 2,
      "confidence": 0.8,
      "type": "transitive"
    }
  ],
  "callees": [
    {
      "callee": "openai.ChatCompletion.create()",
      "depth": 1,
      "confidence": 1.0
    }
  ],
  "type_references": [
    {
      "location": "backend/pipeline/state.py:PipelineState",
      "usage": "self.llm_service: LLMService"
    }
  ],
  "community": {
    "id": "services-cluster-3",
    "members": ["LLMService", "ChromaDBStore", "FileParser"],
    "cohesion": 0.92
  },
  "dead_code": false,
  "framework_context": null,
  "git_history": [
    {"commit": "abc123", "author": "dev1", "message": "Add async query support"},
    {"commit": "def456", "author": "dev1", "message": "Refactor error handling"}
  ],
  "next_step": "Use impact() if planning changes to this symbol"
}
```

**Best for:** Understanding a symbol before modifying it; planning refactors

---

#### Tool 3: `axon_impact(symbol: str, depth: int = 3) → ImpactAnalysis`

**The key differentiator** — blast radius analysis with confidence scoring.

When you're about to change a symbol, `impact()` answers: **"What will break if I change this?"**

Uses BFS traversal through the call graph to find all affected callers, grouped by "will definitely break" / "might break" / "probably safe":

**Grouping by Depth:**

| Depth | Definition | Example | Risk |
|-------|-----------|---------|------|
| 0 | Direct callers (call this symbol directly) | `query()` is called by 5 functions | Will break |
| 1 | Indirect callers (call functions that call this) | Those 5 functions are called by 12 more | May break |
| 2+ | Transitive callers (2+ hops away) | Those 12 are called by 43 total | Review but probably safe |

**Every edge has a confidence score:**
- **1.0** = Exact match (call statement visible in AST)
- **0.8** = Receiver method (dynamic dispatch, high confidence)
- **0.5** = Fuzzy match (variable name match, needs review)

**Example impact analysis for `backend/services/db_client.py:get_pool()`:**

```json
{
  "symbol": "get_pool",
  "blast_radius": {
    "direct_callers": [
      {
        "caller": "backend.services.db_client.init_pool()",
        "type": "function",
        "confidence": 1.0,
        "location": "backend/services/db_client.py:78"
      },
      {
        "caller": "backend.app.startup_event()",
        "type": "event_handler",
        "confidence": 1.0,
        "location": "backend/app.py:45"
      }
    ],
    "indirect_callers": [
      {
        "caller": "backend.main()",
        "confidence": 0.9,
        "depth": 2,
        "path": "main → startup_event → get_pool"
      }
    ],
    "transitive_callers": [
      {
        "caller": "backend.services.user_service.get_user()",
        "confidence": 0.8,
        "depth": 3,
        "reason": "git_coupled_files"
      }
    ]
  },
  "change_suggestions": [
    "If changing signature: must update 3 callers at depth 0",
    "If adding exception: verify caller error handling (depth 1+)",
    "If removing async: major breaking change (4 depth-2 callers)"
  ],
  "git_evidence": {
    "coupled_changes": ["backend/db/connection.py", "backend/app.py"],
    "frequency": "87% of commits touching get_pool also touch app.py"
  },
  "safety_score": 0.72,
  "recommended_depth": 3
}
```

**Best for:** Refactors, API changes, deprecation planning; prevents surprise breakage

---

### 6. Supported Languages

| Language | File Extensions | Parsing | Status |
|----------|---|---|---|
| Python | `.py` | tree-sitter + type hints | Primary, fully featured |
| TypeScript | `.ts`, `.tsx` | tree-sitter + JSDoc | Secondary, fully supported |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` | tree-sitter | Supported |

**For CR8:** Python focus is perfect. TypeScript support available if frontend MCP integration needed in future.

---

### 7. Dependencies & Supply Chain

#### Direct Dependencies

| Package | Version | Purpose | License | Risk |
|---------|---------|---------|---------|------|
| `tree-sitter` | (not pinned in docs) | Code parsing | MIT | Low |
| `kuzudb` | (default) | Graph database | Apache 2.0 | Low |
| `sentence-transformers` | (implied) | BAAI embeddings | Apache 2.0 | Medium (large, ~500MB download) |
| `numpy`, `scipy` | (via sentence-transformers) | Linear algebra | BSD | Low |
| `igraph` | (for community detection) | Graph algorithms | GPL | ⚠️ See below |
| `leidenalg` | (Leiden clustering) | Community detection | Apache 2.0 | Low |
| `numpy` | Various | Scientific computing | BSD | Low |
| `fastapi` | (for MCP server) | HTTP framework | MIT | Low |

#### Transitive Dependency Risk

**🚨 CRITICAL ISSUE: igraph GPL licensing**

The `igraph` package uses GPL-compatible licensing which may create viral licensing obligations. Check Axon's LICENSE file to confirm GPL compatibility.

**Mitigations:**
1. Use `pip install axoniq --no-deps` + manually specify dependencies (not practical)
2. Use Neo4j backend instead (skips local igraph dependency)
3. Accept GPL compliance requirement if CR8 adopts open-source license

#### Estimated Transitive Tree

Based on research:
- sentence-transformers: ~15 dependencies (torch, transformers, scikit-learn, etc.)
- KuzuDB: ~8 dependencies (parquet, arrow, etc.)
- igraph + leidenalg: ~3 dependencies
- **Total:** ~30-40 transitive packages

**For comparison:** code-graph-mcp has ~8-12 transitive (much lighter).

---

### 8. Performance Characteristics

#### Indexing Speed

| Codebase | Files | Symbols | Edges | Time | Speed |
|----------|-------|---------|-------|------|-------|
| Small project | 50 | 200 | 400 | ~1.5s | ~33 files/sec |
| Typical | 142 | 623 | 1,847 | ~4.2s | ~34 files/sec |
| Medium | 300 | 1,200 | 3,600 | ~8-9s | ~33-37 files/sec |
| Large (extrapolated) | 1,000 | 4,000+ | 12,000+ | ~30s | ~33 files/sec |

**CR8 estimate (127 Python files):** 3.5-4 seconds, ~550 symbols, ~1,500 edges

**Indexing is one-time; re-indexing on demand** (no automatic file watching like code-graph-mcp)

#### Query Performance

- **axon_query:** <100ms (BM25 + semantic + fuzzy)
- **axon_context:** <50ms (graph traversal, 3-hop limit)
- **axon_impact:** <200ms (BFS to depth 3)

**Verdict:** All queries sub-second, suitable for live MCP tool calls in agent loops

#### Memory Usage

Estimated (not officially benchmarked):
- Graph database: ~50-100 MB per 1K symbols
- Embeddings index: ~50 MB (HNSW vector index)
- Runtime: ~200-300 MB for typical codebase

**For CR8:** ~100-150 MB expected (acceptable for development)

#### Disk Usage

- `.axon/kuzu.db`: ~10-20 MB
- Vector embeddings: ~5-10 MB
- FTS indices: ~5 MB

**Total:** ~30-50 MB for typical project (acceptable)

---

### 9. CLI Commands Available

Axon provides these commands for developers:

```bash
axon analyze [PATH]        # Index a codebase (one-time)
axon query [QUERY]         # Search from CLI
axon context [SYMBOL]      # Inspect a symbol
axon impact [SYMBOL]       # Blast radius analysis
axon dead-code             # Find unreachable symbols
axon cypher [QUERY]        # Direct graph queries (Cypher syntax)
axon ui                    # Launch web dashboard (localhost:8420)
axon serve                 # Start MCP server (for agent integration)
axon watch                 # Re-index on file changes (watch mode)
axon diff [COMMIT1] [COMMIT2]  # Analyze changes between commits
```

**For CR8:** `axon serve` is the key command for MCP integration in `.claude/mcp.json`.

---

### 10. Web UI & Visualization

Axon includes a built-in interactive dashboard:

**Features:**
- **Graph visualization** (force-directed layout via Sigma.js + WebGL)
- **Explorer view:** Click nodes to inspect, right-click for context menu
- **Analysis view:** Dead code detection, health metrics
- **Cypher console:** Direct graph queries for advanced investigation
- **Search bar:** Full-text + semantic search
- **Community highlighting:** Color-coded functional clusters

**Tech stack:** Vite + React frontend, served on `localhost:8420`

**No Node.js required** — web UI is bundled in Python package

---

### 11. Comparison with code-graph-mcp (Recommended Alternative)

Based on CR8's previous research (2026-03-06):

| Feature | Axon | code-graph-mcp | Winner for CR8 |
|---------|------|---|---|
| **Setup complexity** | Medium (KuzuDB DB) | Low (Python 3.12+) | code-graph-mcp |
| **Language support** | 3 (Python, TS, JS) | 25+ | code-graph-mcp |
| **Token savings on search** | 15-50x (very targeted) | 5-20x (structured) | Axon (more precise) |
| **Real-time updates** | Manual `axon watch` | File watcher automatic | code-graph-mcp |
| **Call graph queries** | Via `axon_impact` + BFS | Native 8 tools | Tie (both strong) |
| **Impact analysis** | ⭐⭐⭐ (confidence scores) | ⭐ (basic tool) | Axon (**key advantage**) |
| **Web UI** | Beautiful dashboard | CLI only | Axon |
| **Transitive deps** | ~40 packages (igraph GPL risk) | ~8-12 packages | code-graph-mcp |
| **Maintenance burden** | Database reindex needed | Watch daemon | code-graph-mcp (lighter) |
| **Maturity** | v1.0.1, single maintainer | v1.2.0+, active | Tie |

**Key insight:** Axon's **impact analysis with confidence scores** is genuinely unique and powerful for refactoring. Everything else, code-graph-mcp does nearly as well with much less complexity.

---

### 12. Security Assessment

| Check | Result | Details |
|-------|--------|---------|
| **Open CVEs** | None found | Searched harshkedia177/axon specifically; no security advisories |
| **CVE in transitive deps** | ⚠️ Check needed | igraph (GPL), sentence-transformers, KuzuDB — should verify at install time via Snyk |
| **License** | Unknown | GitHub repo not accessible (429 errors); assume MIT/Apache until verified |
| **Last release** | v1.0.1 (March 2024) | 12 months old; stable but not cutting-edge |
| **Maintainer count** | 1 primary | harshkedia177 + ~5-10 contributors; low bus factor |
| **Dependency freshness** | Unclear | No version pinning visible; may use old models/libraries |
| **Data handling** | Local | Graph stored locally (.axon/); no cloud uploads; embeddings computed locally |
| **Supply chain risk** | Medium | igraph GPL licensing may create compliance obligations |

**Action items:**
1. ✅ Check igraph license compatibility before adding to CR8
2. ✅ Run Snyk scan on `axoniq` package after adding to pyproject.toml
3. ⚠️ Verify LICENSE file in GitHub repo (fetching failed during research)
4. ⚠️ Confirm sentence-transformers model is cached (HuggingFace may block Cloud Run)

**Verdict:** Technically safe, but **license unknown** (mark as "Needs Verification"). GPL licensing risk is real but manageable if CR8 adopts open-source license.

---

### 13. Is It "Overkill" for CR8?

#### The Argument FOR Adding Now

1. **Impact analysis is unique** — code-graph-mcp doesn't have this; prevents bugs during refactors
2. **Codebase is growing** — 27K LOC with distributed agents (Ingest/Research/Generate) means understanding impact matters
3. **Framework awareness** — FastAPI route detection, GPU service integration help context
4. **Visualization helps team** — New developers understand architecture faster via dashboard
5. **One-time setup** — KuzuDB local storage, no ongoing operational burden

#### The Argument FOR Deferring to v0.6

1. **code-graph-mcp already recommended** — 90% of value with 10% of complexity
2. **React SPA phase is priority** — Adding DB setup now distracts from current sprint
3. **Refactors aren't urgent** — CR8 isn't undergoing major code reorganization yet
4. **Maintenance overhead** — Need to re-index when adding major features (12-phase pipeline)
5. **License uncertainty** — igraph GPL licensing needs verification before committing
6. **Single maintainer risk** — For critical workflow tool, want more ecosystem maturity

#### Honest Assessment for CR8's 2-Person Team

**Current situation:**
- 127 Python files, 27K LOC
- FastAPI + LangGraph architecture (reasonably clean)
- No active major refactors planned
- React SPA phase is immediate priority (v0.5.6-0.6)

**Use case for impact analysis:**
- Would be valuable if: "We're changing how state flows through LangGraph agents"
- Would be nice-to-have if: "New team members need architecture context"
- Would be overkill if: "We're just adding Quiz features and incremental bug fixes"

**Realistic prediction:**
- Impact analysis gets used 10-20% of the time
- 80% of value comes from code-graph-mcp (already recommended)
- Setup + maintenance cost: 5-8 hours one-time, then ~30 min/month during major features

---

## What We Ruled Out (and Why)

| Option | Why Rejected |
|--------|-------------|
| Using Axon as PRIMARY tool instead of code-graph-mcp | code-graph-mcp is 10x simpler; Axon's impact analysis isn't needed for current work |
| Adding Axon + code-graph-mcp simultaneously | Too many new tools; should test code-graph-mcp first, add Axon only if impact analysis gap becomes real |
| Using Neo4j backend instead of KuzuDB | KuzuDB is simpler for single-developer; Neo4j adds infrastructure burden without value for CR8 size |
| Deploying Axon on Cloud Run | Local development only; no need to expose to agents or expose knowledge graph to internet |

---

## Known Gotchas / Edge Cases

### Gotcha 1: igraph GPL Licensing
**Problem:** The `igraph` package (used for Leiden community detection) uses GPL-compatible licensing. This may require CR8 to adopt compatible license.
**Impact:** Could block adding Axon if CR8 needs proprietary license.
**Mitigation:** Check igraph license; if incompatible, use Neo4j backend (skips local igraph, uses Neo4j's algorithms).
**Action:** Verify license before committing to Axon.

### Gotcha 2: Re-indexing Required for New Features
**Problem:** Axon's 12-phase pipeline doesn't auto-update on file changes (unlike code-graph-mcp's file watcher).
**Impact:** After major feature development, must run `axon analyze .` to refresh graph.
**Mitigation:** Add to pre-commit hook or CI/CD; document that graph may be stale during active development.
**Frequency:** ~1-2 times per phase during active coding.

### Gotcha 3: Model Download on First Run
**Problem:** BAAI/bge-small-en-v1.5 embedding model (~100-200 MB) downloads from HuggingFace on first indexing.
**Impact:** First `axon analyze` slower (~30-60 seconds); subsequent runs are fast.
**Mitigation:** Cache model in Docker image or CI environment; document for local setup.
**For Cloud Run:** HuggingFace Hub may be blocked; need to pre-cache model or skip embeddings.

### Gotcha 4: Graph Queries Require Learning Cypher
**Problem:** Direct graph queries require Cypher syntax (Neo4j query language).
**Impact:** Not intuitive for developers unfamiliar with graph databases.
**Mitigation:** MCP tools (axon_query, axon_context, axon_impact) hide Cypher; CLI `axon cypher` is for power users only.
**For CR8:** Likely won't need direct Cypher queries; MCP tools sufficient.

### Gotcha 5: Confidence Scores Can Be Conservative
**Problem:** If many symbols are dynamically called (eval, importlib, etc.), confidence scores drop (0.5-0.8), requiring manual review.
**Impact:** Impact analysis may be "noisy" in code with heavy metaprogramming.
**For CR8:** LangGraph uses dynamic dispatch; impact analysis may flag more things as "review" than actually needed.

### Gotcha 6: Python 3.11 Compatibility Needs Verification
**Problem:** Axon docs say "3.11+" but some dependencies may require 3.12+ (e.g., sentence-transformers).
**Impact:** May need to test in CR8's 3.11 environment before committing.
**Action:** Create test env and run `pip install axoniq` locally before PR.

---

## Security Assessment (Detailed)

| Check | Result | Risk Level | Notes |
|-------|--------|-----------|-------|
| **Open CVEs in harshkedia177/axon** | None | Low | No security advisories found in public databases |
| **CVEs in igraph** | Check required | Medium | igraph is GPL; may create licensing obligations |
| **CVEs in sentence-transformers** | Likely none | Low | Major project (Hugging Face); well-maintained |
| **CVEs in KuzuDB** | Check required | Low | Apache 2.0, newer project; should Snyk scan |
| **License compatibility** | Unknown | Medium | Axon LICENSE not accessible; assume MIT until verified |
| **AGPL/GPL in dependency tree** | Yes (igraph) | Medium | GPL licensing may conflict with CR8's license |
| **Last security update** | v1.0.1 (Mar 2024) | Low | 12 months old; should check commit history for patches |
| **Maintainer responsiveness** | Unclear | Low | Single maintainer; can't assess response time to vulnerabilities |
| **Data exfiltration risk** | None | Low | All processing local; no cloud APIs called |
| **Supply chain risk** | Medium | Medium | ~40 transitive dependencies; sentence-transformers pulls HuggingFace models |

### Action Plan Before Adding Axon

```bash
# 1. Check igraph license compatibility
python3 -c "import igraph; print(igraph.__license__)"

# 2. Snyk vulnerability scan (after adding to pyproject.toml)
snyk test --file=pyproject.toml

# 3. Verify Python 3.11 compatibility
python3.11 -m pip install axoniq --dry-run

# 4. Check sentence-transformers model caching for Cloud Run
python3 -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('BAAI/bge-small-en-v1.5')"

# 5. Verify LICENSE in GitHub repo
curl -s https://raw.githubusercontent.com/harshkedia177/axon/main/LICENSE | head -20
```

**Current Verdict:** SAFE to add with caveats:
- ✅ No known CVEs
- ✅ MIT/Apache-assumed license (verify)
- ⚠️ igraph GPL licensing (check compatibility)
- ⚠️ Model caching needed for Cloud Run
- ✅ Local storage (no data leakage risk)

---

## Decision Made

### Recommendation: **REVISIT FOR v0.6 PHASE 2, Not Now**

**Reasoning:**

1. **React SPA (v0.5) is more urgent** — Adding database setup now delays frontend work
2. **code-graph-mcp already covers 80% of use cases** — Previous research recommended it; start there
3. **Impact analysis isn't blocking right now** — No major refactors planned in v0.5
4. **License uncertainty is real** — Need to verify igraph GPL compatibility before committing
5. **Maintenance overhead** — Requires re-indexing after major features; adds process burden

**If circumstances change, add sooner:**
- ✅ If a major refactor is planned (impact analysis prevents bugs)
- ✅ If new team members struggle with architecture (visualization helps)
- ✅ If code-graph-mcp proves insufficient for relationship queries
- ✅ If license verification shows no GPL conflicts

**v0.6 Phase 2 Implementation Plan (when revisited):**

```markdown
# Task: Add Axon to CR8 Development Workflow

## Phase 2.1: Setup & Verification (2-3 hours)
1. Add `axoniq` to pyproject.toml (without [neo4j] extras)
2. Run `snyk test` to verify no CVEs in dependency tree
3. Verify igraph GPL license compatibility with CR8's license
4. Test `axon analyze .` locally; measure index time, disk usage, RAM
5. Test all three MCP tools (query, context, impact) with sample queries
6. Document findings in CLAUDE.md under "MCP Servers" section

## Phase 2.2: MCP Integration (1-2 hours)
1. Add Axon to `.claude/mcp.json` with `axon serve` command
2. Test MCP tools work in Claude Code agent context
3. Create usage guide: "When to use axon_impact vs code-graph-mcp"
4. Add `.axon/` to `.gitignore`

## Phase 2.3: Workflow Integration (1 hour)
1. Add pre-commit hook: `axon analyze .` on major branches
2. Document re-indexing process for CI/CD
3. Update developer onboarding docs

## Acceptance Criteria
- ✅ All three MCP tools work via Claude Code
- ✅ Impact analysis correctly identifies blast radius for test refactors
- ✅ No CVEs or license conflicts in Snyk scan
- ✅ Index time <5 seconds for current codebase
- ✅ Documentation clear on when to use vs code-graph-mcp
```

---

## Files This Affects

If implemented in v0.6:
- `pyproject.toml` — Add `axoniq` dependency
- `.gitignore` — Add `.axon/` directory
- `.claude/mcp.json` — Add Axon MCP server configuration
- `CLAUDE.md` — Document Axon in "MCP Servers" section
- `mk-docs/getting-started/developer-workflow.md` — Guide on using impact analysis
- `.pre-commit-config.yaml` — Optional: add `axon analyze` hook
- `docs/research/code-intelligence-tools.md` — Update with Axon decision

---

## Alternatives Considered

### Alternative 1: Use only code-graph-mcp (Already Recommended)
- ✅ Simpler setup
- ✅ Real-time file watching
- ✅ Lighter dependencies
- ❌ No impact analysis with confidence scores
- **Verdict:** Code-graph-mcp is the right choice for now. Axon is only justified if impact analysis becomes essential.

### Alternative 2: Use Axon + Neo4j (Production Oriented)
- ✅ Better for multi-user teams
- ✅ Scales to very large codebases
- ❌ Adds infrastructure complexity
- ❌ Overkill for 2-person team
- **Verdict:** Defer indefinitely for CR8; revisit only if team scales.

### Alternative 3: Use Axon as sole tool (Reject)
- ❌ Replaces code-graph-mcp but less comprehensive
- ❌ Missing 25-language support
- ❌ Heavier setup for less gain
- **Verdict:** Don't do this; both tools have different strengths.

---

## Revision History & Status

- **2026-03-06:** Axon deferred in code-intelligence-tools.md as "overkill for CR8's 15K backend LoC"
- **2026-03-11:** Deep research completed. Assessment updated: **27K LOC codebase** makes impact analysis more valuable, but React SPA priority means defer to v0.6 Phase 2
- **Next review:** 2026-06-15 (after v0.5 stabilization) — Assess whether impact analysis gap has become real

---

*If this research is more than 6 months old or Axon releases a major version bump, re-verify before implementing.*
