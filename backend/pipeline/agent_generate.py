import json
import os
import re
import threading
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
from backend.prompts.ppt import (
    STRUCTURE_GAP_SLIDES,
    STRUCTURE_SINGLE_TOPIC_SLIDE,
    STRUCTURE_EXECUTIVE_SUMMARY,
)
from backend.prompts.video import MODULE_TO_SCRIPT, SCRIPT_FROM_SLIDES, HOOK_EXAMPLES

# Module validation thresholds
_MIN_MODULE_CHARS = 2000
_REQUIRED_SECTIONS = ["## Module Overview", "## Learning Objectives", "## Core Content", "## Key Takeaways"]
_MAX_MODULE_RETRIES = 2

# Hook keywords for variety tracking
_HOOK_KEYWORDS = {
    "curiosity": ["what if", "did you know", "ever wonder"],
    "scenario": ["imagine", "picture this", "you're on your first"],
    "statistic": ["percent", "%", "majority of", "studies show"],
    "misconception": ["most students think", "common mistake", "you might think"],
    "value_promise": ["in the next", "by the end", "you'll learn"],
}


# ---------------------------------------------------------------------------
# ChromaDB result caching (#4)
# ---------------------------------------------------------------------------


def _build_chroma_cache(store, topics):
    """Query ChromaDB once for all topics, returns {topic_name: {curriculum_text, research_text}}."""
    cache = {}
    for topic in topics:
        name = topic["name"]
        cur_results = store.query("curriculum", name, n_results=5)
        res_results = store.query("research", name, n_results=5)
        cache[name] = {
            "curriculum_text": "\n\n".join(cur_results["documents"][0]) if cur_results["documents"][0] else "No curriculum content available.",
            "research_text": "\n\n".join(res_results["documents"][0]) if res_results["documents"][0] else "No research content available.",
        }
    return cache


# ---------------------------------------------------------------------------
# Module validation (#10) and retry (#13)
# ---------------------------------------------------------------------------


def _validate_module(module_md, topic_name):
    """Check that a module has required sections and minimum length.

    Returns (is_valid, issues_list).
    """
    issues = []
    if len(module_md) < _MIN_MODULE_CHARS:
        issues.append(f"Too short: {len(module_md)} chars (min {_MIN_MODULE_CHARS})")
    for section in _REQUIRED_SECTIONS:
        if section not in module_md:
            issues.append(f"Missing section: {section}")
    return (len(issues) == 0, issues)


# ---------------------------------------------------------------------------
# Module generation with severity routing (#6) and retry (#13)
# ---------------------------------------------------------------------------


def _generate_module(i, topic, total, chroma_cache, llm_premium, llm_mini, curriculum_scope, gap_lookup, prompt_template=None):
    """Generate a single learning module with severity-based model routing and validation retry.

    Args:
        prompt_template: Optional custom prompt template for eval variant testing.
                        If None, uses the default GENERATE_MODULE prompt.
    """
    name = topic["name"]
    desc = topic.get("description", "")
    techniques = topic.get("key_techniques", [])
    print(f"[Generate] Module {i + 1}/{total}: {name}")

    # Use cached ChromaDB results
    cached = chroma_cache[name]
    curriculum_text = cached["curriculum_text"]
    research_text = cached["research_text"]

    # Get gap analysis and route by severity
    gap_data = gap_lookup.get(name, {})
    gap_text = json.dumps(gap_data, indent=2) if gap_data else "No gap analysis available."
    severity = gap_data.get("severity", "moderate")

    # Severity-based model routing: critical → premium, moderate/minor → mini
    llm = llm_premium if severity == "critical" else llm_mini
    model_label = "premium" if severity == "critical" else "mini"

    template = prompt_template or GENERATE_MODULE
    prompt = template.format(
        topic_name=name,
        topic_description=desc,
        key_techniques=", ".join(techniques) if techniques else "Not specified",
        curriculum_scope=curriculum_scope,
        curriculum_chunks=curriculum_text,
        research_chunks=research_text,
        gap_analysis=gap_text,
    )

    best_result = None
    for attempt in range(_MAX_MODULE_RETRIES + 1):
        response = llm.invoke(prompt, config={"run_name": f"generate_{name}"})
        content = response.content
        is_valid, issues = _validate_module(content, name)

        if is_valid:
            print(f"[Generate]   {name}: done — {len(content)} chars ({model_label}, severity={severity})")
            return content

        best_result = content  # keep best-effort
        if attempt < _MAX_MODULE_RETRIES:
            print(f"[Generate]   {name}: validation failed ({', '.join(issues)}), retrying ({attempt + 1}/{_MAX_MODULE_RETRIES})...")
        else:
            print(f"[Generate]   WARNING: {name}: validation failed after {_MAX_MODULE_RETRIES} retries ({', '.join(issues)}), using best-effort")

    return best_result


# ---------------------------------------------------------------------------
# Script helpers — fallback path
# ---------------------------------------------------------------------------


def _convert_to_script(i, topic_name, module_md, chroma_cache, llm_script):
    """Convert a markdown module into a spoken-word video script (fallback path)."""
    print(f"[Script] Converting module to script: {topic_name}")

    cached = chroma_cache[topic_name]
    prompt = MODULE_TO_SCRIPT.format(
        topic_name=topic_name,
        module_content=module_md,
        curriculum_chunks=cached["curriculum_text"],
        research_chunks=cached["research_text"],
        hook_guidance=HOOK_EXAMPLES,
    )
    response = llm_script.invoke(prompt, config={"run_name": f"script_{topic_name}"})
    script = response.content.strip()
    word_count = len(script.split())
    print(f"[Script]   {topic_name}: ready — {len(script)} chars, {word_count} words (~{word_count // 150}-{word_count // 120} min)")
    return script


def _slugify(name: str) -> str:
    """Convert a topic name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name)
    slug = re.sub(r"[\s]+", "_", slug).strip("_")
    return slug[:80]


def _save_scripts(topics, scripts, scripts_dir, slide_aligned=False):
    """Save video scripts to disk as .txt files."""
    os.makedirs(scripts_dir, exist_ok=True)
    suffix = "_slide" if slide_aligned else ""
    paths = []
    for i, (topic, script) in enumerate(zip(topics, scripts)):
        slug = _slugify(topic["name"])
        filename = f"{i + 1:02d}_{slug}{suffix}.txt"
        path = os.path.join(scripts_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        paths.append(path)
        print(f"[Script]   Saved: {path}")
    return paths


def _generate_scripts(topics, modules_md, chroma_cache, gap_lookup, video_limit):
    """Generate video scripts from markdown modules for the first N topics (fallback path)."""
    video_topics = topics[:video_limit]
    video_modules = modules_md[:video_limit]

    print(f"[Script] Generating scripts for {video_limit} topics (prototype limit)...")

    llm_script = get_llm("premium", temperature=settings.temp_creative)
    scripts = [None] * video_limit
    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _convert_to_script, i, video_topics[i]["name"], video_modules[i], chroma_cache, llm_script
            ): i
            for i in range(video_limit)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            scripts[idx] = future.result()

    return video_topics, scripts


# ---------------------------------------------------------------------------
# PPT fallback (kept from original)
# ---------------------------------------------------------------------------


def _build_fallback_slide_data(gap_summary, curriculum_scope):
    """Build minimal slide data when LLM JSON parsing fails.

    Produces a teaching-focused structure with gap_concepts,
    curriculum_anchor, topic_scores, and priority counts.
    """
    topic_slides = []
    all_gaps = []
    topic_scores = []
    critical_count = 0
    moderate_count = 0
    minor_count = 0

    for g in gap_summary:
        gaps = g.get("gaps", [])
        all_gaps.extend(gaps)
        topic_name = g.get("topic", "Unknown")
        severity = g.get("severity", "moderate")

        # Convert flat gap strings to gap_concepts
        gap_concepts = []
        for gap in gaps[:3]:
            gap_concepts.append({
                "concept_name": gap if isinstance(gap, str) else str(gap),
                "definition": gap if isinstance(gap, str) else str(gap),
                "why_it_matters": "Industry uses this skill in production.",
                "how_it_works": "",
                "impact": "medium",
                "diagram_type": "none",
                "diagram_data": {"nodes": [], "labels": []},
            })

        first_gap = gaps[0] if gaps else topic_name
        topic_slides.append({
            "topic_name": topic_name,
            "slide_title": f"{topic_name}: Industry Concepts to Learn",
            "severity": severity,
            "curriculum_anchor": f"You already know the fundamentals of {topic_name.lower()} from your coursework.",
            "gap_concepts": gap_concepts,
            "misconception": {"wrong": "", "right": ""},
            "quiz": {
                "question": f"Which concept is most critical for industry application of {topic_name.lower()}?",
                "options": [
                    f"A) {first_gap}",
                    "B) Traditional approach only",
                    "C) No additional skills needed",
                    "D) Theoretical knowledge alone",
                ],
                "correct": "A",
                "reflection_prompt": f"Think about how {topic_name.lower()} applies to your career goals.",
            },
            "market_signal": {
                "signal": f"Industry increasingly demands practical {topic_name.lower()} skills beyond academic coverage.",
                "stat": "75%",
                "stat_label": f"of roles require {topic_name.lower()} proficiency",
                "context": f"Employers are looking for candidates who can apply {topic_name.lower()} concepts in real-world settings. Building these skills now gives you a competitive advantage.",
                "supporting_points": [f"Growing demand for {first_gap}", "Industry adoption accelerating", "Skills shortage in the market"],
                "source": "Industry analysis",
            },
            "top_recommendations": [f"Learn: {gap}" for gap in gaps[:3]],
        })

        topic_scores.append({
            "topic": topic_name,
            "curriculum_score": 50,
            "industry_requirement": 80,
        })

        if severity == "critical":
            critical_count += 1
        elif severity == "minor":
            minor_count += 1
        else:
            moderate_count += 1

    return {
        "presentation_title": curriculum_scope,
        "executive_summary": {
            "total_gaps_found": len(all_gaps),
            "topics_analyzed": len(gap_summary),
            "critical_count": critical_count,
            "moderate_count": moderate_count,
            "minor_count": minor_count,
            "critical_gaps": all_gaps[:5],
            "overall_assessment": f"This supplement covers {len(all_gaps)} industry-relevant concepts across {len(gap_summary)} topics to extend your coursework.",
            "topic_scores": topic_scores,
        },
        "topic_slides": topic_slides,
        "recommendations_summary": [],
    }


# ---------------------------------------------------------------------------
# Hook variety enforcement (#9)
# ---------------------------------------------------------------------------


def _detect_hook_type(script_text):
    """Detect which hook type a script uses based on keyword heuristics."""
    lower = script_text[:300].lower()
    for hook_type, keywords in _HOOK_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return hook_type
    return "unknown"


def _get_hook_guidance(used_hooks, lock):
    """Generate hook guidance that emphasizes unused hook types."""
    with lock:
        used = set(used_hooks)
    all_types = set(_HOOK_KEYWORDS.keys())
    unused = all_types - used
    if not unused:
        # All used, reset
        return HOOK_EXAMPLES
    unused_str = ", ".join(unused)
    return f"{HOOK_EXAMPLES}\n\nIMPORTANT: Previous scripts already used these hooks: {', '.join(used)}. For variety, strongly prefer one of the UNUSED types: {unused_str}."


# ---------------------------------------------------------------------------
# PPT parallel structuring (#3)
# ---------------------------------------------------------------------------


def _structure_single_topic_slide(topic, module_md, gap_data, llm_mini, research_text="", prompt_template=None):
    """Structure one topic's PPT slide data via LLM.

    Args:
        research_text: Raw research chunks from ChromaDB for market_signal grounding.
        prompt_template: Optional custom prompt template for eval variant testing.
    """
    name = topic["name"]
    template = prompt_template or STRUCTURE_SINGLE_TOPIC_SLIDE
    prompt = template.format(
        topic_name=name,
        module_content=module_md,
        gap_analysis_json=json.dumps(gap_data, indent=2) if gap_data else "{}",
        research_chunks=research_text or "No raw research data available.",
    )
    response = llm_mini.invoke(
        prompt,
        config={"run_name": f"structure_slide_{name}"},
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        print(f"[Generate] WARNING: Failed to parse slide JSON for {name}, using fallback")
        return None


def _generate_executive_summary(topics, gap_summary, curriculum_scope, llm_nano):
    """Generate executive summary from aggregated gap data."""
    # Aggregate severity counts
    severity_counts = {"critical": 0, "moderate": 0, "minor": 0}
    topic_severities = []
    all_gaps = []
    for g in gap_summary:
        sev = g.get("severity", "moderate")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        topic_severities.append({"topic": g.get("topic", "Unknown"), "severity": sev})
        all_gaps.extend(g.get("gaps", []))

    prompt = STRUCTURE_EXECUTIVE_SUMMARY.format(
        curriculum_scope=curriculum_scope,
        topics_analyzed=len(topics),
        total_gaps_found=len(all_gaps),
        critical_count=severity_counts["critical"],
        moderate_count=severity_counts["moderate"],
        minor_count=severity_counts["minor"],
        topic_severities_json=json.dumps(topic_severities, indent=2),
        critical_gaps_sample=json.dumps(all_gaps[:8], indent=2),
    )
    response = llm_nano.invoke(
        prompt,
        config={"run_name": "structure_executive_summary"},
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        print("[Generate] WARNING: Failed to parse executive summary JSON")
        return None


def _structure_slides_parallel(topics, modules_md, gap_summary, gap_lookup, curriculum_scope, chroma_cache=None):
    """Structure PPT slide data in parallel: per-topic slides + executive summary.

    Falls back to monolithic STRUCTURE_GAP_SLIDES if parallel approach fails.
    """
    total = len(topics)
    llm_mini = get_llm("mini")
    llm_nano = get_llm("nano")
    chroma_cache = chroma_cache or {}

    # Per-topic slides in parallel
    topic_slides = [None] * total
    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _structure_single_topic_slide,
                topics[i], modules_md[i],
                gap_lookup.get(topics[i]["name"], {}),
                llm_mini,
                research_text=chroma_cache.get(topics[i]["name"], {}).get("research_text", ""),
            ): i
            for i in range(total)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            topic_slides[idx] = future.result()

    # Executive summary
    exec_summary = _generate_executive_summary(topics, gap_summary, curriculum_scope, llm_nano)

    # Check for failures — if any topic slide failed, fall back
    if any(ts is None for ts in topic_slides) or exec_summary is None:
        print("[Generate] Parallel PPT structuring had failures, falling back to monolithic approach...")
        return None

    # Assemble full slide_data
    return {
        "presentation_title": curriculum_scope,
        "executive_summary": exec_summary,
        "topic_slides": topic_slides,
        "recommendations_summary": [],
    }


# ---------------------------------------------------------------------------
# PPT-aligned script generation with filtered context (#2) and hook variety (#9)
# ---------------------------------------------------------------------------


def _generate_script_for_topic(idx, topic_slide, topic_module_md, gap_data, chroma_cache, llm_script, used_hooks, hooks_lock, prompt_template=None):
    """Generate one video script aligned to one PPT topic slide.

    Receives ONLY its own topic's module content and gap data (filtered context).

    Args:
        prompt_template: Optional custom prompt template for eval variant testing.
    """
    topic_name = topic_slide.get("topic_name", "Unknown")
    severity = topic_slide.get("severity", "moderate")
    curriculum_anchor = topic_slide.get("curriculum_anchor", "Covered in coursework.")
    misconception = topic_slide.get("misconception", {})
    misconception_wrong = misconception.get("wrong", "")
    misconception_right = misconception.get("right", "")

    print(f"[Script] Topic {idx + 1}: {topic_name} — generating PPT-aligned script...")

    # Use cached ChromaDB results
    cached = chroma_cache.get(topic_name, {})
    curriculum_text = cached.get("curriculum_text", "No curriculum content available.")
    research_text = cached.get("research_text", "No research content available.")

    # Hook variety guidance
    hook_guidance = _get_hook_guidance(used_hooks, hooks_lock)

    template = prompt_template or SCRIPT_FROM_SLIDES
    prompt = template.format(
        topic_name=topic_name,
        severity=severity,
        topic_slide_json=json.dumps(topic_slide, indent=2),
        curriculum_chunks=curriculum_text,
        research_chunks=research_text,
        modules_content=topic_module_md,
        research_context=json.dumps(gap_data, indent=2) if gap_data else "{}",
        curriculum_anchor=curriculum_anchor,
        misconception_wrong=misconception_wrong if misconception_wrong else "No specific misconception identified.",
        misconception_right=misconception_right if misconception_right else "Refer to the gap concepts above for the correct understanding.",
        hook_guidance=hook_guidance,
    )
    response = llm_script.invoke(prompt, config={"run_name": f"script_slide_{topic_name}"})
    script = response.content.strip()

    # Track which hook was used
    hook_type = _detect_hook_type(script)
    with hooks_lock:
        used_hooks.append(hook_type)

    word_count = len(script.split())
    print(f"[Script]   {topic_name}: ready — {len(script)} chars, {word_count} words, hook={hook_type}")
    return script


def _generate_scripts_from_slides(slide_data, topic_modules_map, gap_lookup, chroma_cache, video_limit):
    """Generate per-topic video scripts aligned to PPT topic slides.

    Each topic receives ONLY its own module content and gap data (filtered context).
    Returns (video_topics, scripts) tuple compatible with build_videos.
    """
    topic_slides = slide_data.get("topic_slides", [])[:video_limit]
    total = len(topic_slides)
    print(f"[Script] Generating {total} PPT-aligned scripts (limit: {video_limit})...")

    llm_script = get_llm("premium", temperature=settings.temp_creative)
    scripts = [None] * total
    video_topics = [{"name": ts.get("topic_name", "Unknown")} for ts in topic_slides]

    # Thread-safe hook tracking
    used_hooks = []
    hooks_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {}
        for i in range(total):
            topic_name = topic_slides[i].get("topic_name", "Unknown")
            topic_module = topic_modules_map.get(topic_name, "")
            topic_gap = gap_lookup.get(topic_name, {})
            future = executor.submit(
                _generate_script_for_topic,
                i, topic_slides[i], topic_module, topic_gap,
                chroma_cache, llm_script, used_hooks, hooks_lock,
            )
            future_to_idx[future] = i
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            scripts[idx] = future.result()

    return video_topics, scripts


# ---------------------------------------------------------------------------
# Main generate node
# ---------------------------------------------------------------------------


def generate_node(state: PipelineState) -> dict:
    """Agent 3: Generate learning modules and compile chained outputs.

    Chained flow: PDF (ground truth) -> PPT (structured around PDF) -> Script (synced to PPT).

    Supported formats (via ``settings.output_formats``):
      - ``"pdf"``    -- Build a formatted PDF learning guide.
      - ``"ppt"``    -- Build a gap analysis PowerPoint (structured around PDF, enriched with research).
      - ``"script"`` -- Generate spoken-word video scripts (synced to PPT slides if available).
      - ``"video"``  -- Generate scripts AND render videos via HeyGen API.

    Args:
        state: Pipeline state containing ``topics``, ``curriculum_scope``,
            and ``gap_summary`` from prior stages.

    Returns:
        Dict with ``current_stage`` set to ``"complete"`` and optional keys
        ``pdf_path``, ``ppt_path``, and ``video_dir`` depending on which
        output formats were requested.
    """
    print("[Generate] Starting...")

    store = ChromaStore(settings.chroma_persist_dir)
    topics = state["topics"]
    curriculum_scope = state.get("curriculum_scope", "")
    gap_summary = state.get("gap_summary", [])
    total = len(topics)
    formats = settings.output_formats_list

    # Build lookup and caches upfront
    gap_lookup = {g.get("topic", ""): g for g in gap_summary}
    chroma_cache = _build_chroma_cache(store, topics)

    # Create both LLM tiers for severity-based routing
    llm_premium = get_llm("premium", temperature=settings.temp_structured)
    llm_mini = get_llm("mini")

    # --- Step 1: Generate all markdown modules in parallel (always needed) ---
    modules_md = [None] * total
    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _generate_module, i, topic, total, chroma_cache, llm_premium, llm_mini, curriculum_scope, gap_lookup
            ): i
            for i, topic in enumerate(topics)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            modules_md[idx] = future.result()

    # Build per-topic module map (for filtered context in scripts)
    topic_modules_map = {topics[i]["name"]: modules_md[i] for i in range(total)}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {"current_stage": "complete"}
    slide_data = None

    # --- Step 2 & 3: PDF + PPT in parallel (#1) ---
    needs_pdf = "pdf" in formats
    needs_ppt = "ppt" in formats and gap_summary

    if needs_pdf and needs_ppt:
        # Run PDF build and PPT structuring concurrently
        pdf_path = os.path.join("outputs", f"{timestamp}_learning_guide.pdf")
        with ThreadPoolExecutor(max_workers=2) as executor:
            pdf_future = executor.submit(
                build_pdf,
                title="Market-Enriched Learning Guide",
                topics=topics,
                modules_md=modules_md,
                output_path=pdf_path,
            )
            ppt_future = executor.submit(
                _structure_slides_parallel,
                topics, modules_md, gap_summary, gap_lookup, curriculum_scope, chroma_cache,
            )
            pdf_future.result()
            print(f"[Generate] PDF written to {pdf_path}")
            result["pdf_path"] = pdf_path

            slide_data = ppt_future.result()

        # If parallel PPT structuring failed, fall back to monolithic
        if slide_data is None:
            print("[Generate] Falling back to monolithic PPT structuring...")
            llm_ppt = get_llm("mini")
            modules_content = "\n\n---\n\n".join(
                f"### {topics[i]['name']}\n{md}" for i, md in enumerate(modules_md)
            )
            ppt_prompt = STRUCTURE_GAP_SLIDES.format(
                curriculum_scope=curriculum_scope,
                topic_count=total,
                modules_content=modules_content,
                gap_summary_json=json.dumps(gap_summary, indent=2),
            )
            ppt_response = llm_ppt.invoke(
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
        # Non-parallel paths
        if needs_pdf:
            pdf_path = os.path.join("outputs", f"{timestamp}_learning_guide.pdf")
            build_pdf(
                title="Market-Enriched Learning Guide",
                topics=topics,
                modules_md=modules_md,
                output_path=pdf_path,
            )
            print(f"[Generate] PDF written to {pdf_path}")
            result["pdf_path"] = pdf_path

        if needs_ppt:
            print("[Generate] Structuring slides from PDF content + gap analysis...")
            slide_data = _structure_slides_parallel(
                topics, modules_md, gap_summary, gap_lookup, curriculum_scope, chroma_cache,
            )
            if slide_data is None:
                # Fall back to monolithic
                llm_ppt = get_llm("mini")
                modules_content = "\n\n---\n\n".join(
                    f"### {topics[i]['name']}\n{md}" for i, md in enumerate(modules_md)
                )
                ppt_prompt = STRUCTURE_GAP_SLIDES.format(
                    curriculum_scope=curriculum_scope,
                    topic_count=total,
                    modules_content=modules_content,
                    gap_summary_json=json.dumps(gap_summary, indent=2),
                )
                ppt_response = llm_ppt.invoke(
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

        if "ppt" in formats and not gap_summary:
            print("[Generate] Skipping PPT — no gap data available")

    # --- Step 4: Scripts and/or Videos (per-topic, aligned to PPT if available) ---
    needs_scripts = "script" in formats or "video" in formats
    if needs_scripts:
        video_dir = os.path.join("outputs", f"{timestamp}_videos")
        scripts_dir = os.path.join(video_dir, "scripts")
        video_limit = min(settings.video_topic_limit, total)

        if slide_data is not None:
            # PPT-aligned path: one script per topic slide, filtered context
            video_topics, scripts = _generate_scripts_from_slides(
                slide_data, topic_modules_map, gap_lookup, chroma_cache, video_limit,
            )
            _save_scripts(video_topics, scripts, scripts_dir, slide_aligned=True)
            print(f"[Script] {len(scripts)} PPT-aligned scripts saved to {scripts_dir}")
            result["video_dir"] = video_dir

            if "video" in formats:
                print(f"[Video] Submitting {len(scripts)} PPT-aligned videos...")
                build_videos(
                    topics=video_topics,
                    scripts=scripts,
                    output_dir=video_dir,
                    api_key=settings.heygen_api_key,
                    avatar_id=settings.heygen_avatar_id,
                    voice_id=settings.heygen_voice_id,
                    provider=settings.video_provider,
                    emotion=settings.video_avatar_emotion,
                    speed=settings.video_avatar_speed,
                    max_workers=settings.video_max_workers,
                )
                print(f"[Video] Videos saved to {video_dir}")
        else:
            # Fallback: per-module scripts (no PPT available)
            video_topics, scripts = _generate_scripts(topics, modules_md, chroma_cache, gap_lookup, video_limit)
            _save_scripts(video_topics, scripts, scripts_dir)
            print(f"[Script] {video_limit} per-module scripts saved to {scripts_dir}")
            result["video_dir"] = video_dir

            if "video" in formats:
                print(f"[Video] Submitting {video_limit} videos...")
                build_videos(
                    topics=video_topics,
                    scripts=scripts,
                    output_dir=video_dir,
                    api_key=settings.heygen_api_key,
                    avatar_id=settings.heygen_avatar_id,
                    voice_id=settings.heygen_voice_id,
                    provider=settings.video_provider,
                    emotion=settings.video_avatar_emotion,
                    speed=settings.video_avatar_speed,
                    max_workers=settings.video_max_workers,
                )
                print(f"[Video] Videos saved to {video_dir}")

    # Save raw outputs sidecar for eval framework
    raw_outputs_path = os.path.join("outputs", f"{timestamp}_raw_outputs.json")
    raw_outputs = {}
    for i, topic in enumerate(topics):
        name = topic["name"]
        raw_outputs[name] = {"module_md": modules_md[i] or ""}
    if slide_data is not None:
        for ts in slide_data.get("topic_slides", []):
            name = ts.get("topic_name", "")
            if name in raw_outputs:
                raw_outputs[name]["ppt_json"] = ts
        raw_outputs["_slide_data"] = slide_data
    try:
        with open(raw_outputs_path, "w", encoding="utf-8") as f:
            json.dump(raw_outputs, f, indent=2, ensure_ascii=False)
        print(f"[Generate] Raw outputs saved to {raw_outputs_path}")
    except Exception as e:
        print(f"[Generate] WARNING: Failed to save raw outputs: {e}")

    return result
