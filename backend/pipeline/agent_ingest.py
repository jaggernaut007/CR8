import hashlib
import json

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import settings
from backend.pipeline.state import PipelineState
from backend.services.file_parser import extract_text
from backend.services.llm import get_llm
from backend.services.chromadb_store import ChromaStore
from backend.prompts.ingest import SUMMARIZE_FILE, EXTRACT_TOPICS


def ingest_node(state: PipelineState) -> dict:
    """Agent 1: Parse files, extract topics, populate ChromaDB curriculum collection."""
    print("[Ingest] Starting...")

    store = ChromaStore(settings.chroma_persist_dir)
    store.reset_collections()
    llm = get_llm("mini")

    # 1. Parse all files
    all_pages = []
    for path in state["file_paths"]:
        pages = extract_text(path)
        all_pages.extend(pages)
        print(f"[Ingest] Parsed {pages[0]['source']} — {len(pages)} pages")

    raw_text = "\n\n".join(p["text"] for p in all_pages)

    # 2. Summarize each file (group pages by source)
    files = {}
    for page in all_pages:
        files.setdefault(page["source"], []).append(page["text"])

    summaries = []
    for source, texts in files.items():
        file_text = "\n".join(texts)
        # Truncate to ~15k chars to stay within context limits
        if len(file_text) > 15000:
            file_text = file_text[:15000] + "\n... [truncated]"
        prompt = SUMMARIZE_FILE.format(source=source, text=file_text)
        response = llm.invoke(prompt, config={"run_name": f"summarize_{source}"})
        summaries.append(f"## {source}\n{response.content}")
        print(f"[Ingest] Summarized {source}")

    # 3. Extract topics from combined summaries
    combined = "\n\n".join(summaries)
    prompt = EXTRACT_TOPICS.format(summaries=combined)
    response = llm.invoke(
        prompt,
        config={"run_name": "extract_topics"},
        response_format={"type": "json_object"},
    )
    topics = json.loads(response.content).get("topics", [])
    print(f"[Ingest] Extracted {len(topics)} topics")

    # 4. Chunk and embed into ChromaDB
    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    chunks = splitter.split_text(raw_text)

    ids = [f"cur_{hashlib.md5(c.encode()).hexdigest()[:12]}" for c in chunks]
    metadatas = [{"collection": "curriculum"} for _ in chunks]
    store.add_documents("curriculum", chunks, metadatas, ids)
    print(f"[Ingest] Embedded {len(chunks)} chunks into ChromaDB")

    return {
        "topics": topics,
        "raw_text": raw_text,
        "current_stage": "ingested",
    }
