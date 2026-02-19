import chromadb
from chromadb.errors import NotFoundError


class ChromaStore:
    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)

    def get_or_create_collection(self, name: str) -> chromadb.Collection:
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
        collection = self.get_or_create_collection(collection_name)
        # ChromaDB rejects empty metadata dicts — pass None instead
        if metadatas:
            metadatas = [m if m else None for m in metadatas]
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

    def query(self, collection_name: str, query_text: str, n_results: int = 5) -> dict:
        collection = self.get_or_create_collection(collection_name)
        count = collection.count()
        if count == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        return collection.query(query_texts=[query_text], n_results=min(n_results, count))

    def reset_collections(self):
        for name in ["curriculum", "research"]:
            try:
                self.client.delete_collection(name)
            except (ValueError, NotFoundError):
                pass
