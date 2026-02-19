import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from backend.config import settings
from backend.pipeline.state import PipelineState
from backend.services.llm import get_llm
from backend.services.chromadb_store import ChromaStore
from backend.services.pdf_builder import build_pdf
from backend.services.video_builder import build_videos
from backend.prompts.generate import GENERATE_MODULE
from backend.prompts.video import MODULE_TO_SCRIPT


def _generate_module(i, topic, total, store, llm, curriculum_scope, gap_lookup):
    """Generate a single learning module for one topic."""
    name = topic["name"]
    desc = topic.get("description", "")
    techniques = topic.get("key_techniques", [])
    print(f"[Generate] Module {i + 1}/{total}: {name}")

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
        key_techniques=", ".join(techniques) if techniques else "Not specified",
        curriculum_scope=curriculum_scope,
        curriculum_chunks=curriculum_text,
        research_chunks=research_text,
        gap_analysis=gap_text,
    )
    response = llm.invoke(prompt, config={"run_name": f"generate_{name}"})
    print(f"[Generate]   {name}: done — {len(response.content)} chars")
    return response.content


def _convert_to_script(i, topic_name, module_md, llm_mini):
    """Convert a markdown module into a spoken-word video script."""
    print(f"[Script] Converting module to script: {topic_name}")
    prompt = MODULE_TO_SCRIPT.format(
        topic_name=topic_name,
        module_content=module_md,
    )
    response = llm_mini.invoke(prompt, config={"run_name": f"script_{topic_name}"})
    script = response.content.strip()
    word_count = len(script.split())
    print(f"[Script]   {topic_name}: ready — {len(script)} chars, {word_count} words (~{word_count // 150}-{word_count // 120} min)")
    return script


def _slugify(name: str) -> str:
    """Convert a topic name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name)
    slug = re.sub(r"[\s]+", "_", slug).strip("_")
    return slug[:80]


def _save_scripts(topics, scripts, scripts_dir):
    """Save video scripts to disk as .txt files."""
    os.makedirs(scripts_dir, exist_ok=True)
    paths = []
    for i, (topic, script) in enumerate(zip(topics, scripts)):
        slug = _slugify(topic["name"])
        filename = f"{i + 1:02d}_{slug}.txt"
        path = os.path.join(scripts_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        paths.append(path)
        print(f"[Script]   Saved: {path}")
    return paths


def _generate_scripts(topics, modules_md, video_limit):
    """Generate video scripts from markdown modules for the first N topics."""
    video_topics = topics[:video_limit]
    video_modules = modules_md[:video_limit]

    print(f"[Script] Generating scripts for {video_limit} topics (prototype limit)...")

    llm_mini = get_llm("mini")
    scripts = [None] * video_limit
    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _convert_to_script, i, video_topics[i]["name"], video_modules[i], llm_mini
            ): i
            for i in range(video_limit)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            scripts[idx] = future.result()

    return video_topics, scripts


def generate_node(state: PipelineState) -> dict:
    """Agent 3: Generate learning modules and compile outputs based on selected formats.

    Supported formats (via settings.output_formats):
      - "pdf"    : Build a formatted PDF learning guide
      - "script" : Generate spoken-word video scripts (saved as .txt)
      - "video"  : Generate scripts AND render videos via HeyGen API
    """
    print("[Generate] Starting...")

    store = ChromaStore(settings.chroma_persist_dir)
    llm = get_llm("full")
    topics = state["topics"]
    curriculum_scope = state.get("curriculum_scope", "")
    gap_summary = state.get("gap_summary", [])
    total = len(topics)
    formats = settings.output_formats

    # Build a lookup for gap analysis by topic name
    gap_lookup = {}
    for g in gap_summary:
        gap_lookup[g.get("topic", "")] = g

    # Generate all markdown modules in parallel (always needed as source content)
    modules_md = [None] * total
    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _generate_module, i, topic, total, store, llm, curriculum_scope, gap_lookup
            ): i
            for i, topic in enumerate(topics)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            modules_md[idx] = future.result()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {"current_stage": "complete"}

    # --- PDF ---
    if "pdf" in formats:
        pdf_path = os.path.join("outputs", f"{timestamp}_learning_guide.pdf")
        build_pdf(
            title="Market-Enriched Learning Guide",
            topics=topics,
            modules_md=modules_md,
            output_path=pdf_path,
        )
        print(f"[Generate] PDF written to {pdf_path}")
        result["pdf_path"] = pdf_path

    # --- Scripts and/or Videos ---
    needs_scripts = "script" in formats or "video" in formats
    if needs_scripts:
        video_limit = min(settings.video_topic_limit, total)
        video_dir = os.path.join("outputs", f"{timestamp}_videos")
        scripts_dir = os.path.join(video_dir, "scripts")

        video_topics, scripts = _generate_scripts(topics, modules_md, video_limit)

        # Always save scripts to disk when script or video is requested
        _save_scripts(video_topics, scripts, scripts_dir)
        print(f"[Script] {video_limit} scripts saved to {scripts_dir}")
        result["video_dir"] = video_dir

        # --- Video rendering via HeyGen (only if explicitly requested) ---
        if "video" in formats:
            print(f"[Video] Submitting {video_limit} videos to HeyGen...")
            build_videos(
                topics=video_topics,
                scripts=scripts,
                output_dir=video_dir,
                api_key=settings.heygen_api_key,
                avatar_id=settings.heygen_avatar_id,
                voice_id=settings.heygen_voice_id,
            )
            print(f"[Video] Videos saved to {video_dir}")

    return result
