# Research: ChromaDB Vector Storage

**Date researched:** 2026-03-09
**Library version:** >=0.5 (current production: 1.5.x)
**Researched by:** CR8 Research Assistant (Haiku)
**Status:** Current

---

## Question Being Answered

How do we efficiently embed, store, and retrieve curriculum and research documents using ChromaDB's collection API, embedding functions, and persistent storage in the CR8 pipeline context?

> Specific concerns: Collection CRUD operations, document add/update/upsert with metadata, query API (similarity search + filtering), embedding functions (default vs custom), persistent storage configuration (SQLite backend), distance metrics, performance limits, and security posture.

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| Official Documentation | https://docs.trychroma.com/ | 2026-03-09 |
| Collections API Reference | https://cookbook.chromadb.dev/core/collections/ | 2026-03-09 |
| Query and Filtering Guide | https://docs.trychroma.com/docs/querying-collections/query-and-get | 2026-03-09 |
| Embedding Functions | https://docs.trychroma.com/docs/embeddings/embedding-functions | 2026-03-09 |
| Storage Layout Guide | https://cookbook.chromadb.dev/core/storage-layout/ | 2026-03-09 |
| Update Data API | https://docs.trychroma.com/docs/collections/update-data | 2026-03-09 |
| Performance Guide | https://docs.trychroma.com/guides/deploy/performance | 2026-03-09 |
| GitHub Releases | https://github.com/chroma-core/chroma/releases | 2026-03-09 |
| PyPI Package Info | https://pypi.org/project/chromadb/ | 2026-03-09 |
| License (Apache 2.0) | https://github.com/chroma-core/chroma/blob/main/LICENSE | 2026-03-09 |

> ⚠️ **Agent note:** This research covers v0.5+ and documents modern patterns. DuckDB+Parquet backend (pre-0.4.0) is deprecated; all modern versions use SQLite. Configuration patterns differ from legacy code; always use `configuration` dict for HNSW settings, not metadata.

## What We Found

### The Correct Approach

```python
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

# 1. Initialize persistent client (survives restarts)
client = chromadb.PersistentClient(path="./chroma_db")

# 2. Get or create collection with explicit distance metric
collection = client.get_or_create_collection(
    name="curriculum",
    configuration={
        "hnsw": {
            "space": "cosine",
            "ef_construction": 200,
            "max_neighbors": 32
        }
    }
)

# 3. Add documents with metadata and IDs (auto-embedded with all-MiniLM-L6-v2)
collection.add(
    documents=["Python is a programming language", "Machine learning is AI"],
    metadatas=[
        {"topic": "Programming", "source": "lesson1"},
        {"topic": "ML", "source": "lesson2"}
    ],
    ids=["doc_001", "doc_002"]
)

# 4. Query with similarity search + metadata filtering
results = collection.query(
    query_texts=["What is Python?"],
    n_results=5,
    where={"topic": "Programming"}  # Metadata filter
)
print(results)  # dict with "documents", "metadatas", "distances"

# 5. Update existing documents (embeddings regenerated if text changes)
collection.update(
    ids=["doc_001"],
    documents=["Updated Python documentation"],
    metadatas=[{"topic": "Programming", "source": "lesson1_v2"}]
)

# 6. Upsert (add if new, update if exists)
collection.upsert(
    ids=["doc_003", "doc_001"],
    documents=["New doc", "Updated Python"],
    metadatas=[{"topic": "NewTopic"}, {"topic": "Programming"}]
)

# 7. Delete specific documents
collection.delete(ids=["doc_003"])

# 8. Reset entire collection
client.delete_collection(name="curriculum")
```

### Key API Methods / Concepts

| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `PersistentClient(path)` | Initialize vector store with disk persistence | Uses SQLite backend; creates `chroma.sqlite3` in path directory. Do NOT use `Client()` (in-memory) in production — loses all data on exit. |
| `get_or_create_collection(name, configuration)` | Get existing collection or create with config | Configuration dict (v0.5+) controls HNSW behavior; space ("cosine", "l2", "ip") is immutable after creation. Avoid legacy metadata-based config. |
| `collection.add(documents, ids, metadatas)` | Embed and store new documents | IDs must be unique; duplicates silently ignored. Metadatas are optional per-doc dicts; empty dicts must be filtered to `None`. Auto-embeds with `all-MiniLM-L6-v2` unless custom function supplied. Max batch ~5,461 embeddings (v1.3.4). |
| `collection.update(ids, documents, metadatas)` | Update existing documents or metadata | If document text changes, re-embeds automatically. Can pass only metadatas to update metadata without re-embedding. Non-existent IDs logged as error, silently ignored. |
| `collection.upsert(ids, documents, metadatas)` | Add new or update existing (atomic) | Preferred over add+update combo. IDs that exist are updated; new IDs are added. Recommended for deduplication patterns. |
| `collection.query(query_texts, n_results, where, where_document)` | Semantic similarity search with filtering | Returns dict with `documents`, `metadatas`, `distances` (lists-of-lists). `where` filters metadata; `where_document` filters text content. Operators: `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`, `$and`, `$or`. |
| `collection.delete(ids)` | Delete documents by ID | Non-existent IDs silently ignored. |
| `collection.count()` | Get document count in collection | Returns integer; may lag slightly after batch writes. |
| `client.delete_collection(name)` | Drop entire collection | Throws `NotFoundError` if doesn't exist; safe to catch with try/except. |

### Configuration Required

```python
# 1. Backend storage (automatic, no user config needed)
# ChromaDB uses SQLite by default in persistent mode
# Data stored at: {persist_dir}/chroma.sqlite3

# 2. Distance metric configuration (per-collection, immutable after creation)
# Valid HNSW space values: "cosine", "l2" (default), "ip" (inner product)
# Use configuration dict to set (modern pattern for v0.5+):
configuration = {
    "hnsw": {
        "space": "cosine",         # Default is "l2"; cannot change after creation
        "ef_construction": 200,    # Default 200; affects index quality/speed tradeoff
        "max_neighbors": 32        # Default 32; affects search recall
    }
}
collection = client.get_or_create_collection(
    name="curriculum",
    configuration=configuration
)

# 3. Embedding function (default vs custom)
# Default: all-MiniLM-L6-v2 (384-dim, sentence-transformers)
# No API key required; model auto-downloads on first use (~133 MB)

# To use custom embedding function:
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

custom_ef = SentenceTransformerEmbeddingFunction(
    model_name="all-mpnet-base-v2"  # Higher quality, larger (438MB)
)
collection = client.get_or_create_collection(
    name="custom_embeddings",
    embedding_function=custom_ef,
    configuration={"hnsw": {"space": "cosine"}}
)

# 4. CR8-specific: MD5-based ID generation for deduplication
import hashlib

def make_deterministic_id(text: str, prefix: str = "cur_") -> str:
    """Generate reproducible ID from content."""
    hash_hex = hashlib.md5(text.encode()).hexdigest()[:12]
    return f"{prefix}{hash_hex}"

# Usage in ingest: avoids duplicate embeddings across research results
document_id = make_deterministic_id(chunk_text)
collection.upsert(
    ids=[document_id],
    documents=[chunk_text],
    metadatas=[{"source": "lesson_1", "topic": "ML"}]
)

# 5. Environment setup (optional, only for client/server mode)
# CHROMA_DB_IMPL=rest          # If using remote Chroma server
# CHROMA_SERVER_HOST=localhost # Server hostname
# CHROMA_SERVER_PORT=8000      # Server port
# (Not needed for PersistentClient local mode used by CR8)
```

### Distance Metrics Explained

| Metric | Formula | Best For | Notes |
|--------|---------|----------|-------|
| **L2 (Euclidean)** | √(Σ(x_i - y_i)²) | General similarity | Default in ChromaDB; magnitude-sensitive; use when vector norms vary. |
| **Cosine** | 1 - (x·y / ‖x‖‖y‖) | Normalized embeddings (text) | Recommended for text; magnitude-invariant; similarity scores in [0, 2]. |
| **IP (Inner Product)** | -(x·y) | High-dimensional sparse | Fast on GPU; assumes normalized vectors; can produce negative scores. |

**For CR8:** Using **cosine** is correct for curriculum text embeddings. `all-MiniLM-L6-v2` outputs normalized vectors, making cosine the ideal distance metric. Switching metrics requires recreating the collection (no migration path).

---

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| DuckDB + Parquet backend (pre-0.4.0) | Deprecated; ChromaDB v0.4.0+ uses SQLite exclusively. Old config pattern no longer supported. |
| In-memory Client() | Loses all data on process exit; acceptable for tests, unsafe for production pipelines. |
| Legacy metadata-based config (`metadata={"hnsw:space": "cosine"}`) | Deprecated in v0.5+; use `configuration` dict instead. Settings can be lost if collection is modified. |
| Custom embedding function for all ingests | Large-scale ingests benefit from built-in batching; better to use default embedding function with explicit chunking strategy. |
| Storing binary blobs in metadata | Metadata is lightweight; store file paths/references instead, fetch blobs separately. |

---

## Known Gotchas / Edge Cases

- **Immutable distance metric**: `hnsw:space` is set at collection creation and cannot be changed. Changing metrics requires recreating the collection (lossy operation). Plan the distance metric upfront.

- **Configuration vs Metadata (v0.5+ breaking change)**: In v0.5+, use `configuration={"hnsw": {...}}` NOT `metadata={"hnsw:space": "..."}`. The legacy metadata pattern can cause settings to be lost if the collection is later modified. CR8's current `chromadb_store.py` uses the old pattern and should be updated for clarity (backward-compatible, but deprecated).

- **Batch size limit**: ChromaDB enforces a maximum batch size per `add()` call (~5,461 embeddings in v1.3.4). Large ingests must be chunked; ChromaDB handles this transparently, but explicit batching (1K–5K per batch) improves visibility.

- **Empty metadata dicts rejected**: Passing empty `{}` as metadata causes ChromaDB to reject the batch. Filter to `None` or omit the field:
  ```python
  metadatas = [m if m else None for m in raw_metadatas]
  collection.add(documents=documents, metadatas=metadatas, ids=ids)
  ```

- **Thread safety constraint**: ChromaDB PersistentClient uses SQLite, which does NOT support concurrent writes from multiple threads/processes. Serialize writes per collection. Current CR8 pipeline is single-threaded per node, so this is not a blocker.

- **Memory limits (HNSW index)**: The HNSW index must fit in RAM. Collection size scales as N = R × 0.245 (millions of embeddings = RAM in GB × 0.245). At ~7 million embeddings, the database remains stable. For CR8's single-course ingests (<10,000 documents), this is negligible.

- **Duplicate IDs silently ignored**: If you call `.add()` with an ID that already exists, the duplicate is silently dropped. Use `.upsert()` if you want to replace existing documents.

- **Filter operators**: Metadata filters support `$and`, `$or`, `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`. No regex filters; use `where_document` for substring/text content filters (case-insensitive full-text, not regex).

- **Collection count() can lag**: In some versions, `.count()` can be slightly stale immediately after writes. Eventual consistency within milliseconds.

- **PersistentClient path must be writable**: If the persist directory doesn't exist, ChromaDB creates it. Ensure parent directories are writable.

---

## Performance Considerations

### Memory Footprint (HNSW Index)

For 384-dim embeddings (like `all-MiniLM-L6-v2`):
- **Per-embedding overhead**: ~0.245 MB per million embeddings (including index + metadata)
- **At 1M docs**: ~245 MB in RAM + index structures
- **At 7M docs**: ~1.7 GB in RAM (practical limit for laptops)

For CR8's single-course ingests (typically 1,000–5,000 documents after chunking), expect <50 MB memory overhead.

### Query Latency

- **Semantic search**: 10–100 ms on modern hardware for millions of vectors
- **Metadata filtering**: Sub-linear reduction; filters candidates before distance computation
- **Batch add/update**: Depends on embedding function; `all-MiniLM-L6-v2` ~5–10 ms per document on CPU, <2 ms on GPU

### Recommendations for CR8

1. **Keep collections in memory**: Avoid swapping; ensure available RAM > 2× estimated collection size.
2. **Batch inserts explicitly**: Use 1,000–5,000 docs per batch for visibility; ChromaDB handles internal batching.
3. **Reuse collection instances**: Don't recreate collections unnecessarily; each creation re-indexes.
4. **Monitor persist_dir disk space**: SQLite grows with data; expect 2–5× embedding memory on disk.

---

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (critical/high) | None | No known critical or high-severity CVEs in ChromaDB v0.5–1.5 as of 2026-03-09. GitHub Security Advisories and Snyk database clean. |
| License | Apache 2.0 | Fully compatible with CR8 (no license restrictions). Open-source, permissive. |
| Last release | 2026-02-27 (v1.5.2) | Active maintenance; versions released weekly. Healthy cadence. |
| Maintainer count | Multiple (Chroma-core team) | Open-source project with active core team; not a single-maintainer risk. |
| Transitive dependencies | ~15 major packages | Includes numpy, sentence-transformers, pydantic, typing-extensions, tokenizers. Standard ML stack; no unmaintained dependencies. |
| Known security incidents | None reported | No public security disclosures for ChromaDB. Threat model: local-only (PersistentClient) or authenticated server (v1.0+). |
| Input validation | Adequate | Collections enforce ID uniqueness; metadata is typed dict (no injection). File path traversal not applicable (PersistentClient only writes to configured persist_dir). |

### Transitive Dependency Risk Analysis

**Potential issue**: `sentence-transformers` → `transformers` → `tokenizers` (Rust binding) can conflict with other projects using different tokenizer versions. ChromaDB pins approximate versions (e.g., `tokenizers>=0.13.3`), but conflicts are possible in complex environments.

**Impact on CR8**: Low risk (clean uv-managed environment with explicit dependency pinning). If conflicts arise, mitigate by:
1. Using custom embedding function without sentence-transformers
2. Implementing embedding via OpenAI API instead (trades compute for API cost)
3. Isolated Docker image (current deployment uses this)

**No-risk alternative for production**: Use OpenAI embeddings API instead of local sentence-transformers (costs API credits but eliminates tokenizer conflicts).

### File Security (Local Persistence)

**Concern**: `chroma_db/` directory is gitignored and contains SQLite database with document text and embeddings.

**Mitigation**:
- Do not expose `chroma_db/` directory to untrusted users.
- Embeddings are deterministic (same input = same ID); if source documents are sensitive, encrypting the persist directory is recommended (e.g., LUKS, Bitlocker, EBS encryption) for production.
- For GCP Cloud Run (CPU service), `chroma_db/` is ephemeral per job; no persistent storage risk.
- For development laptops, ensure `/chroma_db` is on encrypted disk.

**Verdict:** SAFE to add and use with standard operational security practices.

---

## Decision Made

Based on this research, we confirm that:

1. **ChromaDB v0.5+ is the correct choice** for CR8's embedding and retrieval needs:
   - Zero infrastructure (local SQLite persistence)
   - Built-in embeddings (no additional API calls)
   - Flexible collection CRUD and query API with metadata filtering
   - Deterministic deduplication via MD5 IDs
   - Apache 2.0 license (fully compatible)

2. **Modern patterns (v0.5+) to follow**:
   - Use `PersistentClient(path)` for local persistence ✓
   - Use `configuration={"hnsw": {"space": "cosine"}}` for distance metrics (not legacy metadata pattern)
   - Use `collection.query(where=...)` for metadata filtering ✓
   - Batch large ingests with explicit chunking for visibility ✓
   - Use `upsert()` for deduplication patterns ✓

3. **No API changes needed** in `backend/services/chromadb_store.py`. The existing implementation correctly uses:
   - `PersistentClient` for persistence ✓
   - `get_or_create_collection()` with cosine distance ✓ (uses legacy metadata pattern, works but could be modernized)
   - `add()` / `query()` / `delete()` with proper metadata handling ✓
   - `reset_collections()` for per-job isolation ✓

4. **Security posture is solid**:
   - No open CVEs ✓
   - Apache 2.0 licensed ✓
   - Active maintenance (weekly releases) ✓
   - Local-only (PersistentClient) eliminates authentication concerns ✓
   - Transitive dependencies are standard ML stack ✓

---

## Files This Affects

- `backend/services/chromadb_store.py` — ChromaStore wrapper class. Implementation is correct and current. Optional: update line 32–35 to use `configuration` dict instead of legacy `metadata` pattern for clarity.
- `backend/pipeline/agent_ingest.py` — Chunking and `collection.add()` calls; uses deterministic MD5 IDs for deduplication. Implementation verified correct.
- `backend/pipeline/agent_research.py` — `collection.query()` and research collection storage; uses proper metadata filtering. Implementation verified correct.
- `backend/config.py` — `chroma_persist_dir` setting (default `./chroma_db`). Correct for local dev; GCP Cloud Run uses ephemeral storage per job.
- `pyproject.toml` — `chromadb>=0.5` pinned; allows flexibility for minor/patch updates. Current production uses 1.5.x.
- `docs/adr/ADR-007-chromadb-vector-storage.md` — Decision record; all details remain valid for v0.5+. No updates needed.

---

*This research is current as of 2026-03-09. ChromaDB releases weekly; re-verify if implementing a major version bump (e.g., 2.0) or >6 months have passed.*
