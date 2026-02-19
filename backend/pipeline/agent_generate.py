import json
import os
from datetime import datetime

from backend.config import settings
from backend.pipeline.state import PipelineState
from backend.services.llm import get_llm
from backend.services.chromadb_store import ChromaStore
from backend.services.pdf_builder import build_pdf
from backend.prompts.generate import GENERATE_MODULE


def generate_node(state: PipelineState) -> dict:
    """Agent 3: Generate learning modules and compile into PDF."""
    print("[Generate] Starting...")

    store = ChromaStore(settings.chroma_persist_dir)
    llm = get_llm("full")
    topics = state["topics"]
    gap_summary = state.get("gap_summary", [])

    # Build a lookup for gap analysis by topic name
    gap_lookup = {}
    for g in gap_summary:
        gap_lookup[g.get("topic", "")] = g

    modules_md = []
    for i, topic in enumerate(topics):
        name = topic["name"]
        desc = topic.get("description", "")
        print(f"[Generate] Module {i + 1}/{len(topics)}: {name}")

        # Retrieve from both collections
        cur_results = store.query("curriculum", name, n_results=5)
        res_results = store.query("research", name, n_results=5)

        curriculum_text = "\n\n".join(cur_results["documents"][0]) if cur_results["documents"][0] else "No curriculum content available."
        research_text = "\n\n".join(res_results["documents"][0]) if res_results["documents"][0] else "No research content available."

        # Get gap analysis for this topic
        gap_data = gap_lookup.get(name, {})
        gap_text = json.dumps(gap_data, indent=2) if gap_data else "No gap analysis available."

        prompt = GENERATE_MODULE.format(
            topic_name=name,
            topic_description=desc,
            curriculum_chunks=curriculum_text,
            research_chunks=research_text,
            gap_analysis=gap_text,
        )
        response = llm.invoke(prompt, config={"run_name": f"generate_{name}"})
        modules_md.append(response.content)
        print(f"[Generate]   Done — {len(response.content)} chars")

    # Compile PDF
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join("outputs", f"{timestamp}_learning_guide.pdf")

    build_pdf(
        title="Market-Enriched Learning Guide",
        topics=topics,
        modules_md=modules_md,
        output_path=output_path,
    )
    print(f"[Generate] PDF written to {output_path}")

    return {
        "pdf_path": output_path,
        "current_stage": "complete",
    }
