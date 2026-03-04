import logging

import chromadb
from chromadb.errors import NotFoundError

logger = logging.getLogger(__name__)


class ChromaStore:
    """Persistent ChromaDB vector store for curriculum and research embeddings.

    Wraps a ``chromadb.PersistentClient`` and provides convenience methods
    for adding, querying, and resetting the two pipeline collections
    (``curriculum`` and ``research``).  All collections use cosine similarity.

    Args:
        persist_dir: Filesystem path where ChromaDB stores its data.
    """

    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)

    def get_or_create_collection(self, name: str) -> chromadb.Collection:
        """Get an existing collection or create a new one with cosine distance.

        Args:
            name: Name of the ChromaDB collection.

        Returns:
            The ``chromadb.Collection`` instance.
        """
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ):
        """Add documents to a named collection.

        Args:
            collection_name: Target collection (e.g. ``"curriculum"``).
            documents: List of text strings to embed and store.
            metadatas: Optional per-document metadata dicts.
            ids: Optional unique IDs; must match length of *documents*.
        """
        collection = self.get_or_create_collection(collection_name)
        if not documents:
            return
        # ChromaDB rejects empty metadata dicts — pass None instead
        if metadatas:
            metadatas = [m if m else None for m in metadatas]
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        logger.debug("Added %d documents to '%s'", len(documents), collection_name)

    def query(self, collection_name: str, query_text: str, n_results: int = 5) -> dict:
        """Semantic similarity search against a named collection.

        Args:
            collection_name: Collection to query.
            query_text: Natural-language query string.
            n_results: Maximum number of results to return.

        Returns:
            Dict with ``documents``, ``metadatas``, and ``distances`` lists,
            each wrapped in an outer list (ChromaDB batch format).  Returns
            empty inner lists when the collection has no documents.
        """
        collection = self.get_or_create_collection(collection_name)
        count = collection.count()
        if count == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        return collection.query(query_texts=[query_text], n_results=min(n_results, count))

    def reset_collections(self):
        """Delete and recreate the ``curriculum`` and ``research`` collections.

        Silently ignores collections that do not exist.
        """
        for name in ["curriculum", "research"]:
            try:
                self.client.delete_collection(name)
            except (ValueError, NotFoundError):
                pass
