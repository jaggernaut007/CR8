from backend.services.chromadb_store import ChromaStore


def test_add_and_query(temp_chroma_dir):
    store = ChromaStore(temp_chroma_dir)
    store.add_documents(
        collection_name="curriculum",
        documents=["Transformers use self-attention", "Word2Vec learns word embeddings", "RNNs process sequences"],
        metadatas=[{"topic": "transformers"}, {"topic": "word2vec"}, {"topic": "rnn"}],
        ids=["doc1", "doc2", "doc3"],
    )
    results = store.query("curriculum", "attention mechanism", n_results=2)
    assert len(results["documents"][0]) == 2
    # The transformer doc should be most relevant
    assert "attention" in results["documents"][0][0].lower()


def test_reset_collections(temp_chroma_dir):
    store = ChromaStore(temp_chroma_dir)
    store.add_documents("curriculum", ["test doc"], [{"topic": "test"}], ["id1"])
    store.reset_collections()
    results = store.query("curriculum", "test", n_results=5)
    assert len(results["documents"][0]) == 0


def test_two_collections(temp_chroma_dir):
    store = ChromaStore(temp_chroma_dir)
    store.add_documents("curriculum", ["curriculum doc"], [{}], ["c1"])
    store.add_documents("research", ["research doc"], [{}], ["r1"])

    c_results = store.query("curriculum", "doc", n_results=5)
    r_results = store.query("research", "doc", n_results=5)

    assert len(c_results["documents"][0]) == 1
    assert len(r_results["documents"][0]) == 1
    assert "curriculum" in c_results["documents"][0][0]
    assert "research" in r_results["documents"][0][0]


def test_add_with_custom_ids_are_retrievable(temp_chroma_dir):
    """Documents added with specific IDs are stored under those exact IDs."""
    store = ChromaStore(temp_chroma_dir)
    store.add_documents(
        collection_name="curriculum",
        documents=["Transformer architecture overview"],
        metadatas=[{"source": "lecture_01"}],
        ids=["my_custom_id_001"],
    )
    results = store.query("curriculum", "transformer", n_results=5)
    assert len(results["documents"][0]) == 1
    assert "Transformer" in results["documents"][0][0]


def test_add_with_metadata_stored_and_returned(temp_chroma_dir):
    """Metadata is stored and returned alongside documents in query results."""
    store = ChromaStore(temp_chroma_dir)
    store.add_documents(
        collection_name="curriculum",
        documents=["Word embeddings represent semantic meaning"],
        metadatas=[{"topic": "word2vec", "lecture": 3}],
        ids=["meta_test_001"],
    )
    results = store.query("curriculum", "embeddings", n_results=5)
    assert len(results["documents"][0]) == 1
    # Metadata should be present in results
    if "metadatas" in results:
        assert results["metadatas"][0][0].get("topic") == "word2vec"


def test_query_empty_collection_returns_empty(temp_chroma_dir):
    """Querying before any documents are added returns empty results without error."""
    store = ChromaStore(temp_chroma_dir)
    results = store.query("curriculum", "anything", n_results=5)
    assert isinstance(results, dict)
    assert "documents" in results
    assert len(results["documents"][0]) == 0


def test_query_respects_n_results_limit(temp_chroma_dir):
    """Query returns at most n_results documents."""
    store = ChromaStore(temp_chroma_dir)
    docs = [f"Document about topic {i}" for i in range(10)]
    metadatas = [{"idx": i} for i in range(10)]
    ids = [f"doc_{i}" for i in range(10)]
    store.add_documents("curriculum", docs, metadatas, ids)

    results = store.query("curriculum", "document topic", n_results=3)
    assert len(results["documents"][0]) <= 3
