# ChromaDB Store

**File**: `backend/services/chromadb_store.py`

Wrapper around ChromaDB's persistent client. Manages two collections for semantic search over curriculum and research content.

## Collections

| Collection | Content | Populated by |
|------------|---------|-------------|
| `curriculum` | Chunked text from source materials (1,500-char chunks, 150-char overlap) | Agent 1: Ingest |
| `research` | Web search results and enrichment content from gap analysis | Agent 2: Research |

Uses ChromaDB's built-in `all-MiniLM-L6-v2` embeddings -- local, free, no API calls.

## Usage

```python
from backend.services.chromadb_store import ChromaStore

store = ChromaStore("./chroma_db")

# Add documents
store.add_documents(
    "curriculum",
    documents=["text..."],
    metadatas=[{"source": "file.pdf"}],
    ids=["doc_1"],
)

# Query
results = store.query("curriculum", "attention mechanism", n_results=5)
# Returns: {"documents": [["..."]], "metadatas": [[{...}]], "distances": [[0.3, ...]]}

# Reset (deletes both collections)
store.reset_collections()
```

## Class Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `(persist_dir: str)` | Create persistent ChromaDB client |
| `get_or_create_collection` | `(name: str)` | Get or create a collection |
| `add_documents` | `(collection_name, documents, metadatas=None, ids=None)` | Add docs to collection |
| `query` | `(collection_name, query_text, n_results=5)` | Semantic search |
| `reset_collections` | `()` | Delete curriculum and research collections |
