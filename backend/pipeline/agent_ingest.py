import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import settings
from backend.pipeline.state import PipelineState
from backend.services.file_parser import extract_text
from backend.services.llm import get_llm
from backend.services.chromadb_store import ChromaStore
from backend.prompts.ingest import SUMMARIZE_FILE, EXTRACT_TOPICS


def _summarize_file(source, texts, llm):
    """Summarize a single file's text."""
    file_text = "\n".join(texts)
    if len(file_text) > 15000:
        file_text = file_text[:15000] + "\n... [truncated]"
    prompt = SUMMARIZE_FILE.format(source=source, text=file_text)
    response = llm.invoke(prompt, config={"run_name": f"summarize_{source}"})
    print(f"[Ingest] Summarized {source}")
    return f"## {source}\n{response.content}"


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

    # 2. Summarize each file in parallel
    files = {}
    for page in all_pages:
        files.setdefault(page["source"], []).append(page["text"])

    summaries = [None] * len(files)
    file_items = list(files.items())
    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(_summarize_file, source, texts, llm): idx
            for idx, (source, texts) in enumerate(file_items)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            summaries[idx] = future.result()

    # 3. Extract topics from combined summaries
    combined = "\n\n".join(summaries)
    prompt = EXTRACT_TOPICS.format(summaries=combined)
    response = llm.invoke(
        prompt,
        config={"run_name": "extract_topics"},
        response_format={"type": "json_object"},
    )
    data = json.loads(response.content)
    topics = data.get("topics", [])
    curriculum_scope = data.get("curriculum_scope", "")
    print(f"[Ingest] Scope: {curriculum_scope}")
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
        "curriculum_scope": curriculum_scope,
        "current_stage": "ingested",
    }
