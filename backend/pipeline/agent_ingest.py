import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import settings
from backend.pipeline.state import PipelineCancelledError, PipelineState, _check_cancelled
from backend.services.file_parser import extract_text
from backend.services.llm import get_llm
from backend.services.chromadb_store import ChromaStore
from backend.prompts.ingest import (
    SUMMARIZE_FILE,
    SUMMARIZE_CHUNK,
    REDUCE_SUMMARIES,
    EXTRACT_TOPICS,
)

logger = logging.getLogger(__name__)

# Map-reduce summarization thresholds (tuned empirically):
#   - 15k chars fits within GPT-5-nano's context with room for the prompt template
#   - 12k chunks don't need overlap because each chunk is independently summarized
#     then reduced into a single summary
#   - 500k hard cap prevents sending a 200-page PDF as a single mega-prompt (~$0.50+)
_MAP_REDUCE_THRESHOLD = 15000   # chars — files longer than this use map-reduce
_CHUNK_SIZE = 12000             # chars per map chunk
_MAX_FILE_CHARS = 500_000       # hard cap: ~125k tokens — prevents runaway cost on huge PDFs

# Control-character regex: strips null bytes and non-printable characters that
# can confuse tokenizers or be used to hide injection payloads in PDFs.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize(text: str) -> str:
    """Strip control characters and enforce a character cap on raw document text.

    This is the trust boundary between untrusted PDF content and the prompt
    construction layer. It does not prevent all prompt injection, but it
    removes common obfuscation vectors (null bytes, hidden characters).
    """
    text = _CONTROL_CHAR_RE.sub("", text)
    return text[:_MAX_FILE_CHARS]


def _summarize_file(source, texts, llm):
    """Summarize a single file's text, using map-reduce for long files."""
    file_text = _sanitize("\n".join(texts))

    if len(file_text) <= _MAP_REDUCE_THRESHOLD:
        # Short file — direct summarization
        prompt = SUMMARIZE_FILE.format(source=source, text=file_text)
        response = llm.invoke(prompt, config={"run_name": f"summarize_{source}"})
        logger.info("Summarized %s (direct)", source)
        return f"## {source}\n{response.content}"

    # Long file — map-reduce: split → summarize chunks → combine
    chunks = [
        file_text[i : i + _CHUNK_SIZE]
        for i in range(0, len(file_text), _CHUNK_SIZE)
    ]
    total = len(chunks)
    logger.info("%s: %d chars -> map-reduce (%d chunks)", source, len(file_text), total)

    # Map phase: summarize each chunk
    chunk_summaries = []
    for idx, chunk in enumerate(chunks):
        prompt = SUMMARIZE_CHUNK.format(
            source=source, chunk_num=idx + 1, total_chunks=total, text=chunk,
        )
        resp = llm.invoke(prompt, config={"run_name": f"summarize_{source}_chunk{idx}"})
        chunk_summaries.append(resp.content)

    # Reduce phase: combine chunk summaries into one
    prompt = REDUCE_SUMMARIES.format(
        source=source,
        chunk_summaries="\n\n---\n\n".join(
            f"Chunk {i+1}:\n{s}" for i, s in enumerate(chunk_summaries)
        ),
    )
    response = llm.invoke(prompt, config={"run_name": f"reduce_{source}"})
    logger.info("Summarized %s (map-reduce, %d chunks)", source, total)
    return f"## {source}\n{response.content}"


def ingest_node(state: PipelineState) -> dict:
    """Agent 1: Parse files, extract topics, populate ChromaDB curriculum collection.

    Workflow:
        1. Parse all uploaded files (PDF/PPTX) into pages of text.
        2. Summarize each file (direct or map-reduce for long files).
        3. Extract structured topics from combined summaries via LLM.
        4. Chunk and embed raw text into the ChromaDB ``curriculum``
           collection for downstream retrieval.

    Args:
        state: Pipeline state containing ``file_paths`` to process.

    Returns:
        Dict with ``topics`` (list of topic dicts), ``raw_text``
        (concatenated extracted text), ``curriculum_scope`` (one-sentence
        domain boundary), and ``current_stage`` set to ``"ingested"``.
    """
    logger.info("Starting ingest")

    store = ChromaStore(settings.chroma_persist_dir)
    store.reset_collections()
    llm = get_llm("nano")

    # 1. Parse all files
    all_pages = []
    for path in state["file_paths"]:
        pages = extract_text(path)
        if not pages:
            logger.warning("No text extracted from %s, skipping", path)
            continue
        all_pages.extend(pages)
        logger.info("Parsed %s - %d pages", pages[0]["source"], len(pages))

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
            _check_cancelled()
            idx = future_to_idx[future]
            try:
                summaries[idx] = future.result()
            except PipelineCancelledError:
                raise
            except Exception as exc:
                source = file_items[idx][0]
                logger.exception("Summarization failed for '%s'", source)
                summaries[idx] = f"## {source}\n\n*Summarization failed: {exc}*"

    # 3. Extract topics from combined summaries
    combined = "\n\n".join(summaries)
    prompt = EXTRACT_TOPICS.format(summaries=combined)
    response = llm.invoke(
        prompt,
        config={"run_name": "extract_topics"},
        response_format={"type": "json_object"},
    )
    try:
        data = json.loads(response.content)
        topics = data.get("topics", [])
        curriculum_scope = data.get("curriculum_scope", "")
    except json.JSONDecodeError:
        logger.warning("Malformed JSON from LLM during topic extraction, using single-topic fallback")
        topics = [{"name": "Curriculum Overview", "description": "Full curriculum content", "key_techniques": []}]
        curriculum_scope = "General curriculum content"
    logger.info("Scope: %s", curriculum_scope)
    logger.info("Extracted %d topics", len(topics))

    # 4. Chunk and embed into ChromaDB
    # 1500-char chunks with 150-char overlap give good retrieval granularity:
    # small enough for precise semantic matches, overlapping enough to avoid
    # splitting mid-sentence.  These differ from the map-reduce chunks above
    # because retrieval needs fine-grained passages, not coarse summaries.
    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    chunks = splitter.split_text(raw_text)

    ids = [f"cur_{hashlib.md5(c.encode()).hexdigest()[:12]}" for c in chunks]
    metadatas = [{"collection": "curriculum"} for _ in chunks]
    store.add_documents("curriculum", chunks, metadatas, ids)
    logger.info("Embedded %d chunks into ChromaDB", len(chunks))

    return {
        "topics": topics,
        "raw_text": raw_text,
        "curriculum_scope": curriculum_scope,
        "current_stage": "ingested",
    }
