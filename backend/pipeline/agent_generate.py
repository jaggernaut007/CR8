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
from backend.services.ppt_builder import build_gap_ppt
from backend.services.video_builder import build_videos
from backend.prompts.generate import GENERATE_MODULE
from backend.prompts.ppt import STRUCTURE_GAP_SLIDES
from backend.prompts.video import MODULE_TO_SCRIPT, SCRIPT_FROM_SLIDES


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


def _build_fallback_slide_data(gap_summary, curriculum_scope):
    """Build minimal slide data when LLM JSON parsing fails."""
    topic_slides = []
    all_gaps = []
    for g in gap_summary:
        gaps = g.get("gaps", [])
        all_gaps.extend(gaps)
        topic_slides.append({
            "topic_name": g.get("topic", "Unknown"),
            "slide_title": g.get("topic", "Unknown"),
            "severity": "moderate",
            "curriculum_summary": g.get("curriculum_coverage", ""),
            "industry_summary": g.get("industry_demands", ""),
            "gaps": [{"gap_title": gap, "description": gap, "impact": "medium"} for gap in gaps[:5]],
            "top_recommendations": [f"Address gap: {gap}" for gap in gaps[:3]],
        })
    return {
        "presentation_title": f"Gap Analysis: {curriculum_scope}",
        "executive_summary": {
            "total_gaps_found": len(all_gaps),
            "critical_gaps": all_gaps[:5],
            "overall_assessment": f"Analysis of {len(gap_summary)} topics found {len(all_gaps)} gaps.",
        },
        "topic_slides": topic_slides,
        "recommendations_summary": [],
    }


def _generate_script_from_slides(slide_data, modules_content, gap_summary):
    """Generate a single video script synced to PPT slides, drawing from PDF + research."""
    print("[Script] Generating slide-synced script from PPT + PDF + research...")
    llm_mini = get_llm("mini")
    prompt = SCRIPT_FROM_SLIDES.format(
        slide_data_json=json.dumps(slide_data, indent=2),
        modules_content=modules_content,
        research_context=json.dumps(gap_summary, indent=2),
    )
    response = llm_mini.invoke(prompt, config={"run_name": "script_from_slides"})
    script = response.content.strip()
    word_count = len(script.split())
    print(f"[Script] Slide-synced script ready — {len(script)} chars, {word_count} words")
    return script


def generate_node(state: PipelineState) -> dict:
    """Agent 3: Generate learning modules and compile chained outputs.

    Chained flow: PDF (ground truth) → PPT (structured around PDF) → Script (synced to PPT).

    Supported formats (via settings.output_formats):
      - "pdf"    : Build a formatted PDF learning guide
      - "ppt"    : Build a gap analysis PowerPoint (structured around PDF, enriched with research)
      - "script" : Generate spoken-word video scripts (synced to PPT slides if available)
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

    # --- Step 1: Generate all markdown modules in parallel (always needed) ---
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

    # Build a combined modules string (reused by PPT and slide-synced scripts)
    modules_content = "\n\n---\n\n".join(
        f"### {topics[i]['name']}\n{md}" for i, md in enumerate(modules_md)
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {"current_stage": "complete"}
    slide_data = None  # Will be set if PPT is generated; scripts can chain off it

    # --- Step 2: PDF (ground truth) ---
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

    # --- Step 3: PPT (structured around PDF, enriched with research/gaps) ---
    if "ppt" in formats:
        if gap_summary:
            print("[Generate] Structuring slides from PDF content + gap analysis...")
            llm_mini = get_llm("mini")
            ppt_prompt = STRUCTURE_GAP_SLIDES.format(
                curriculum_scope=curriculum_scope,
                topic_count=total,
                modules_content=modules_content,
                gap_summary_json=json.dumps(gap_summary, indent=2),
            )
            ppt_response = llm_mini.invoke(
                ppt_prompt,
                config={"run_name": "structure_gap_slides"},
                response_format={"type": "json_object"},
            )
            try:
                slide_data = json.loads(ppt_response.content)
            except json.JSONDecodeError:
                print("[Generate] WARNING: Failed to parse slide JSON, using fallback")
                slide_data = _build_fallback_slide_data(gap_summary, curriculum_scope)

            ppt_path = os.path.join("outputs", f"{timestamp}_gap_analysis.pptx")
            build_gap_ppt(slide_data=slide_data, output_path=ppt_path)
            print(f"[Generate] PPT written to {ppt_path}")
            result["ppt_path"] = ppt_path
        else:
            print("[Generate] Skipping PPT — no gap data available")

    # --- Step 4: Scripts and/or Videos (synced to PPT if available) ---
    needs_scripts = "script" in formats or "video" in formats
    if needs_scripts:
        video_dir = os.path.join("outputs", f"{timestamp}_videos")
        scripts_dir = os.path.join(video_dir, "scripts")

        if slide_data is not None:
            # Chained path: script synced to PPT slides, content from PDF + research
            script = _generate_script_from_slides(slide_data, modules_content, gap_summary)
            os.makedirs(scripts_dir, exist_ok=True)
            script_path = os.path.join(scripts_dir, "gap_analysis_script.txt")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script)
            print(f"[Script] Slide-synced script saved to {script_path}")
            result["video_dir"] = video_dir

            # For video rendering, pass the full script as a single-item list
            if "video" in formats:
                print("[Video] Submitting slide-synced video to HeyGen...")
                build_videos(
                    topics=[{"name": "Gap Analysis Presentation"}],
                    scripts=[script],
                    output_dir=video_dir,
                    api_key=settings.heygen_api_key,
                    avatar_id=settings.heygen_avatar_id,
                    voice_id=settings.heygen_voice_id,
                )
                print(f"[Video] Video saved to {video_dir}")
        else:
            # Fallback: per-module scripts (no PPT available)
            video_limit = min(settings.video_topic_limit, total)
            video_topics, scripts = _generate_scripts(topics, modules_md, video_limit)
            _save_scripts(video_topics, scripts, scripts_dir)
            print(f"[Script] {video_limit} per-module scripts saved to {scripts_dir}")
            result["video_dir"] = video_dir

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
