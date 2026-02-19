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
