# ADR-007: ChromaDB for Vector Storage
<!-- Architecture Decision Record
     Place in: docs/adr/ADR-007-chromadb-vector-storage.md
     Foundational v0.1 decision — backfilled for agent reference. -->

**Date:** 2026-01-15
**Status:** Accepted
**Deciders:** Shreyas Jagannath

---

## Context

The CR8 pipeline requires a vector store to embed and retrieve curriculum content.
During the Ingest phase, raw PDF/PPTX text is chunked (1500 chars, 150 overlap) and
embedded into a "curriculum" collection. During the Research phase, those embeddings
are queried to ground gap analysis in actual course material, and web search results
are stored in a "research" collection for downstream generation.

Key constraints at v0.1:

- **Local-first development** — the pipeline must run entirely on a developer laptop
  with no cloud services beyond OpenAI and Tavily.
- **Zero marginal cost** — embedding and retrieval should not incur per-query API fees.
- **Single-user, single-job** — collections are reset at the start of each pipeline run;
  there is no need for multi-tenant isolation or concurrent writes.
- **Simple integration** — the vector store is a supporting service, not the product;
  setup and maintenance burden must be minimal.

## Decision

> We will use ChromaDB (local persistent mode) as the vector store for curriculum
> and research embeddings because it requires zero infrastructure, zero cost, and
> provides a Python-native API that fits the single-user pipeline model.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **ChromaDB local (chosen)** | Zero cost; no API key; `pip install`; built-in MiniLM embeddings; persistent storage via SQLite+parquet; cosine/L2/IP distance | No horizontal scaling; no multi-user concurrency; embedded model quality ceiling; single-machine only |
| Pinecone (managed) | Fully managed; scales to billions of vectors; low-latency globally; metadata filtering | Paid service ($70+/mo for production); cloud dependency; API key required; vendor lock-in on index format |
| Weaviate | Rich schema + hybrid search (BM25 + vector); GraphQL API; multi-modal support | Heavy setup (Docker or Weaviate Cloud); overkill for single-user pipeline; steeper learning curve |
| pgvector (PostgreSQL) | Colocates with app DB (Neon); SQL-native queries; ACID transactions on embeddings | Requires Neon pgvector extension; adds schema complexity; embedding model must be managed separately; slower for pure ANN workloads than purpose-built stores |
| FAISS (Facebook) | Extremely fast ANN search; GPU-accelerated; battle-tested at scale | No built-in persistence (must serialize/deserialize manually); no metadata storage; no built-in embedding; library-level, not a database |

## Consequences

**Positive:**

- Zero infrastructure — `chromadb>=0.5` is the only dependency; no Docker, no cloud account.
- Built-in embeddings — ChromaDB defaults to `all-MiniLM-L6-v2`, so no separate embedding
  service or API calls are needed. This keeps the Ingest node self-contained.
- Fast iteration — `chroma_db/` is gitignored and recreated on each run; no migration
  scripts or index management.
- Deterministic deduplication — MD5 hash-based IDs prevent duplicate embeddings across
  research results without external coordination.

**Negative / Trade-offs:**

- **No multi-user scaling** — ChromaDB's PersistentClient uses SQLite under the hood,
  which does not support concurrent writers. If CR8 moves to multi-tenant SaaS, the
  vector store must be replaced or fronted with a queue.
- **Embedding model is fixed** — the default MiniLM model is adequate for curriculum
  retrieval but may underperform on specialized domains. Switching models would require
  re-embedding all data and potentially changing the ChromaDB configuration.
- **No cloud backup** — embeddings exist only on the local filesystem. Loss of
  `chroma_db/` requires a full re-ingest (acceptable since source PDFs are retained).

**Neutral:**

- Collections are ephemeral per pipeline run — `reset_collections()` clears both
  `curriculum` and `research` at the start of each job. This is a design choice,
  not a limitation of ChromaDB.
- If pgvector is later adopted for the app database (Neon), vector storage could
  migrate there. ChromaDB's simple interface makes this a low-risk swap.

## Implementation Notes

- **Files affected:**
  - `backend/services/chromadb_store.py` — `ChromaStore` class (90 lines, thin wrapper)
  - `backend/pipeline/agent_ingest.py` — creates store, resets collections, embeds chunks
  - `backend/pipeline/agent_research.py` — queries curriculum, stores research results
  - `backend/config.py` — `chroma_persist_dir` setting (default `./chroma_db`)
  - `pyproject.toml` — `chromadb>=0.5` dependency
- **Patterns to follow:**
  - Always access ChromaDB through `ChromaStore`, never import `chromadb` directly in agents.
  - Use `get_or_create_collection` with explicit `hnsw:space` metadata.
  - Generate deterministic IDs via `hashlib.md5(doc.encode()).hexdigest()[:12]` with a
    prefix (`cur_`, `res_`, `enr_`) to namespace by collection purpose.
- **Things to avoid:**
  - Do not use ChromaDB's in-memory client (`Client()`) in production — it loses data
    on process exit. Always use `PersistentClient`.
  - Do not store large binary blobs in ChromaDB metadata — keep metadata lightweight
    (topic name, type tag).
  - Do not assume thread-safety for writes to the same collection from multiple workers;
    the current code serializes writes per collection within each agent node.

## References

- [ChromaDB documentation](https://docs.trychroma.com/)
- `backend/services/chromadb_store.py` — service implementation
- `backend/pipeline/agent_ingest.py` — chunking and embedding
- `backend/pipeline/agent_research.py` — research storage with dedup
- `backend/CLAUDE.md` — service registry listing ChromaDB with MiniLM embeddings
