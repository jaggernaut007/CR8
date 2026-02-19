import hashlib
import json

from backend.config import settings
from backend.pipeline.state import PipelineState
from backend.services.llm import get_llm
from backend.services.chromadb_store import ChromaStore
from backend.services.web_search import search
from backend.prompts.research import GAP_ANALYSIS


def research_node(state: PipelineState) -> dict:
    """Agent 2: Research each topic, identify gaps, store enrichments."""
    print("[Research] Starting...")

    store = ChromaStore(settings.chroma_persist_dir)
    llm = get_llm("mini")
    topics = state["topics"]
    gap_summary = []

    for i, topic in enumerate(topics):
        name = topic["name"]
        desc = topic.get("description", "")
        print(f"[Research] Topic {i + 1}/{len(topics)}: {name}")

        # 1. Web search — job skills + industry trends
        job_results = search(f"{name} job requirements skills 2025 2026", max_results=5)
        trend_results = search(f"{name} industry trends applications 2025 2026", max_results=5)

        job_text = "\n".join(
            f"- {r.get('title', '')}: {r.get('content', '')[:300]}" for r in job_results
        )
        trend_text = "\n".join(
            f"- {r.get('title', '')}: {r.get('content', '')[:300]}" for r in trend_results
        )

        # 2. Retrieve curriculum context
        cur_results = store.query("curriculum", name, n_results=3)
        curriculum_text = "\n".join(cur_results["documents"][0]) if cur_results["documents"][0] else "No curriculum content found."

        # 3. Gap analysis via LLM
        prompt = GAP_ANALYSIS.format(
            topic_name=name,
            topic_description=desc,
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

        gap_summary.append(analysis)
        gap_count = len(analysis.get("gaps", []))
        print(f"[Research]   Found {gap_count} gaps")

        # 4. Store research in ChromaDB (deduplicate by ID)
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

    print(f"[Research] Completed — {len(gap_summary)} topics analyzed")
    return {
        "gap_summary": gap_summary,
        "current_stage": "researched",
    }
