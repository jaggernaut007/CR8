import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.config import settings
from backend.pipeline.state import PipelineCancelledError, PipelineState, _check_cancelled
from backend.services.llm import get_llm
from backend.services.chromadb_store import ChromaStore
from backend.services.web_search import search
from backend.prompts.research import GAP_ANALYSIS

logger = logging.getLogger(__name__)


def _research_topic(i, topic, total, store, llm, curriculum_scope):
    """Process a single topic: web search, gap analysis, store results."""
    name = topic["name"]
    desc = topic.get("description", "")
    techniques = topic.get("key_techniques", [])
    domain_ctx = topic.get("domain_context", name)
    print(f"[Research] Topic {i + 1}/{total}: {name}")

    # 1. Web search — two parallel Tavily queries per topic:
    #   - "skills/applications" query: surfaces job market relevance
    #   - "developments/alternatives" query: surfaces industry trends
    # Running in parallel halves the wall-clock time per topic.
    technique_str = ", ".join(techniques[:4]) if techniques else name
    with ThreadPoolExecutor(max_workers=2) as search_pool:
        job_future = search_pool.submit(
            search, f"{technique_str} skills applications in {domain_ctx} 2025 2026", 5
        )
        trend_future = search_pool.submit(
            search, f"{name} latest developments alternatives in {domain_ctx} 2025 2026", 5
        )
        try:
            job_results = job_future.result(timeout=30)
        except PipelineCancelledError:
            raise
        except Exception as exc:
            print(f"[Research] WARNING: job search failed for '{name}': {exc}")
            job_results = []
        try:
            trend_results = trend_future.result(timeout=30)
        except PipelineCancelledError:
            raise
        except Exception as exc:
            print(f"[Research] WARNING: trend search failed for '{name}': {exc}")
            trend_results = []

    job_text = "\n".join(
        f"- {r.get('title', '')}: {r.get('content', '')[:300]}" for r in job_results
    )
    trend_text = "\n".join(
        f"- {r.get('title', '')}: {r.get('content', '')[:300]}" for r in trend_results
    )

    # 2. Retrieve curriculum context — 3 results is enough to ground the gap
    #    analysis without flooding the prompt (each result is ~1500 chars)
    cur_results = store.query("curriculum", name, n_results=3)
    curriculum_text = "\n".join(cur_results["documents"][0]) if cur_results["documents"][0] else "No curriculum content found."

    # 3. Gap analysis via LLM
    prompt = GAP_ANALYSIS.format(
        topic_name=name,
        topic_description=desc,
        key_techniques=", ".join(techniques) if techniques else "Not specified",
        curriculum_scope=curriculum_scope,
        curriculum_chunks=curriculum_text,
        job_results=job_text or "No results found.",
        trend_results=trend_text or "No results found.",
    )
    response = llm.invoke(
        prompt,
        config={"run_name": f"gap_analysis_{name}"},
        response_format={"type": "json_object"},
    )

    try:
        analysis = json.loads(response.content)
    except json.JSONDecodeError:
        analysis = {"topic": name, "gaps": [], "enrichments": []}

    gap_count = len(analysis.get("gaps", []))
    print(f"[Research]   {name}: found {gap_count} gaps")

    # 4. Store research in ChromaDB — deduplicate using MD5 hash prefix.
    #    12-char hex prefix gives 48 bits of entropy (~2.8 × 10^14 possible IDs),
    #    far exceeding our typical corpus size.  MD5 is fine here because this
    #    is a dedup key, not a security hash.
    seen_ids = set()
    research_docs = []
    research_ids = []
    research_meta = []

    for r in job_results + trend_results:
        doc = f"{r.get('title', '')}: {r.get('content', '')}"
        doc_id = f"res_{hashlib.md5(doc.encode()).hexdigest()[:12]}"
        if doc_id not in seen_ids:
            seen_ids.add(doc_id)
            research_docs.append(doc)
            research_ids.append(doc_id)
            research_meta.append({"topic": name, "type": "search_result"})

    for e in analysis.get("enrichments", []):
        doc = f"{e.get('title', '')}: {e.get('why_it_matters', '')} -- {', '.join(e.get('key_concepts', []))}"
        doc_id = f"enr_{hashlib.md5(doc.encode()).hexdigest()[:12]}"
        if doc_id not in seen_ids:
            seen_ids.add(doc_id)
            research_docs.append(doc)
            research_ids.append(doc_id)
            research_meta.append({"topic": name, "type": "enrichment"})

    if research_docs:
        store.add_documents("research", research_docs, research_meta, research_ids)

    return analysis


def research_node(state: PipelineState) -> dict:
    """Agent 2: Research each topic, identify gaps, store enrichments.

    For each topic extracted by Agent 1, this node:
        1. Runs parallel web searches for skills/applications and trends.
        2. Retrieves relevant curriculum chunks from ChromaDB.
        3. Performs LLM-based gap analysis comparing curriculum to industry.
        4. Stores research results and enrichments in the ChromaDB
           ``research`` collection.

    Args:
        state: Pipeline state containing ``topics`` and ``curriculum_scope``
            from the Ingest stage.

    Returns:
        Dict with ``gap_summary`` (list of per-topic gap analysis dicts,
        each containing ``topic``, ``gaps``, ``enrichments``, and
        ``severity``) and ``current_stage`` set to ``"researched"``.
    """
    print("[Research] Starting...")

    store = ChromaStore(settings.chroma_persist_dir)
    llm = get_llm("mini", temperature=settings.temp_analysis)
    topics = state["topics"]
    curriculum_scope = state.get("curriculum_scope", "")
    total = len(topics)

    # Process all topics in parallel
    gap_summary = [None] * total
    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(_research_topic, i, topic, total, store, llm, curriculum_scope): i
            for i, topic in enumerate(topics)
        }
        for future in as_completed(future_to_idx):
            _check_cancelled()
            idx = future_to_idx[future]
            try:
                gap_summary[idx] = future.result()
            except PipelineCancelledError:
                raise
            except Exception as exc:
                topic_name = topics[idx]["name"]
                print(f"[Research] ERROR: topic '{topic_name}' failed — {exc}")
                gap_summary[idx] = {"topic": topic_name, "gaps": [], "enrichments": [], "severity": "minor"}

    print(f"[Research] Completed — {len(gap_summary)} topics analyzed")
    return {
        "gap_summary": gap_summary,
        "current_stage": "researched",
    }
