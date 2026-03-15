"""Agent 3: Generate learning modules and compile chained outputs (PDF, PPT, Script, Video)."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from backend.config import settings
from backend.pipeline.state import PipelineCancelledError, PipelineState, _check_cancelled
from backend.services.llm import get_llm
from backend.services.chromadb_store import ChromaStore
from backend.services.pdf_builder import build_pdf
from backend.services.ppt_builder import build_gap_ppt
from backend.services.file_parser import export_slides_as_images
from backend.services.video_builder import build_videos
from backend.prompts.generate import GENERATE_MODULE
from backend.prompts.ppt import (
    STRUCTURE_GAP_SLIDES,
    STRUCTURE_SINGLE_TOPIC_SLIDE,
    STRUCTURE_EXECUTIVE_SUMMARY,
)
from backend.prompts.video import MODULE_TO_SCRIPT, SCRIPT_FROM_SLIDES, HOOK_EXAMPLES

logger = logging.getLogger(__name__)

# Module validation thresholds:
#   - 2000 chars is the floor for a meaningful module (roughly 300 words).
#     Below this, the LLM has likely produced a stub or truncated output.
#   - Required sections match the GENERATE_MODULE prompt's output schema;
#     if a section is missing, the module failed to follow the prompt structure.
_MIN_MODULE_CHARS = 2000
_REQUIRED_SECTIONS = ["## Module Overview", "## Learning Objectives", "## Core Content", "## Key Takeaways"]

# Maximum retries for module generation when validation fails.
# 2 retries (3 total attempts) balances quality vs. API cost.
_MAX_MODULE_RETRIES = 2

# Hook keywords: video scripts open with a "hook" (first ~300 chars).
# We track which hook types have been used across topics to encourage variety.
# Each type maps to keywords that identify it in the opening text.
_HOOK_KEYWORDS = {
    "curiosity": ["what if", "did you know", "ever wonder"],
    "scenario": ["imagine", "picture this", "you're on your first"],
    "statistic": ["percent", "%", "majority of", "studies show"],
    "misconception": ["most students think", "common mistake", "you might think"],
    "value_promise": ["in the next", "by the end", "you'll learn"],
}


# ---------------------------------------------------------------------------
# Context classes — reduce argument passing (PLR0913)
# ---------------------------------------------------------------------------


class _VideoJobInputs:
    """Groups the video dispatch arguments to satisfy PLR0913 (max 5 args)."""

    __slots__ = (
        "ppt_path", "scripts", "slide_images", "topic_slide_map",
        "video_dir", "video_topics",
    )

    def __init__(  # noqa: PLR0913
        self,
        video_topics: list[dict],
        scripts: list[str],
        video_dir: str,
        slide_images: list[str],
        topic_slide_map: dict[str, list[int]] | None = None,
        ppt_path: str | None = None,
    ) -> None:
        self.video_topics = video_topics
        self.scripts = scripts
        self.video_dir = video_dir
        self.slide_images = slide_images
        self.topic_slide_map = topic_slide_map
        self.ppt_path = ppt_path


class _GenerateCtx:
    """Shared context for the generate phase — reduces argument passing (PLR0913).

    Fields are set by ``_init_generate_ctx`` and updated by helper functions.
    Core fields: topics, curriculum_scope, gap_summary, gap_lookup, chroma_cache,
    llm_premium, llm_mini, formats, timestamp.
    Mutable output fields: modules_md, topic_modules_map, slide_data, ppt_path,
    topic_slide_map.
    """


class _ScriptCtx:
    """Script generation context — wraps _GenerateCtx with script-specific state."""

    __slots__ = ("gen", "hooks_lock", "llm_script", "used_hooks")

    def __init__(self, gen_ctx, llm_script, used_hooks, hooks_lock):
        self.gen = gen_ctx
        self.llm_script = llm_script
        self.used_hooks = used_hooks
        self.hooks_lock = hooks_lock


# ---------------------------------------------------------------------------
# Video dispatch
# ---------------------------------------------------------------------------


def _build_videos_dispatch(state: PipelineState, inputs: _VideoJobInputs) -> None:
    """Route video generation to remote services or local fallback.

    When remote video services are configured (GPU or CPU-video), uses the
    2-tier fallback chain: GPU primary -> CPU-video.
    Local ``build_videos()`` is only used when no service URLs are set
    (local development).
    """
    if settings.should_use_video_service:
        _build_videos_gpu(state, inputs)
        return

    # Local fallback — only when no video service URLs are configured (dev mode)
    _check_cancelled()
    build_videos(
        topics=inputs.video_topics,
        scripts=inputs.scripts,
        output_dir=inputs.video_dir,
        cancel_check=_check_cancelled,
        **_video_kwargs(inputs.slide_images, inputs.topic_slide_map),
    )


def _build_videos_gpu(state: PipelineState, inputs: _VideoJobInputs) -> None:
    """Try GPU services (primary then fallback). Raises on total failure."""
    from backend.services.gcs_client import GCSVideoClient
    from backend.services.gpu_client import VideoServiceClient

    gcs = GCSVideoClient()
    gpu = VideoServiceClient()
    job_id = state["job_id"]
    needs_remote_export = bool(inputs.ppt_path and not inputs.slide_images)
    pptx_name = os.path.basename(inputs.ppt_path) if needs_remote_export else None
    manifest = _build_gpu_manifest(job_id, inputs, pptx_name)
    pptx_upload = inputs.ppt_path if needs_remote_export else None

    completed = False
    try:
        _submit_and_download_gpu(gcs, gpu, job_id, inputs, manifest, pptx_upload)
        completed = True
    finally:
        if not completed:
            try:
                gcs.cleanup_job(job_id)
            except Exception:
                logger.warning("GCS cleanup failed for job %s", job_id)


def _submit_and_download_gpu(gcs, gpu, job_id, inputs, manifest, pptx_upload):  # noqa: PLR0913
    """Upload inputs to GCS, submit to GPU service, and download results."""
    pptx_name = manifest.get("pptx_name")
    logger.info("Uploading %s to GCS: job=%s", "PPTX" if pptx_name else "slides", job_id)
    gcs_prefix = gcs.upload_job_inputs(
        job_id, inputs.slide_images, manifest, pptx_path=pptx_upload,
    )
    _check_cancelled()
    logger.info("Submitting video job to GPU service: job=%s", job_id)
    video_job_id = gpu.submit_job(job_id, gcs_prefix)
    logger.info("GPU job submitted: video_job_id=%s region=%s", video_job_id, gpu.base_url)
    gpu.poll_until_complete(video_job_id, cancel_check=_check_cancelled)
    logger.info("Downloading completed videos from GCS: job=%s", job_id)
    gcs.download_videos(job_id, inputs.video_dir)


def _build_gpu_manifest(job_id: str, inputs: _VideoJobInputs, pptx_name: str | None) -> dict:
    """Build the manifest dict sent to the GPU video service via GCS."""
    return {
        "job_id": job_id,
        "topics": inputs.video_topics,
        "scripts": inputs.scripts,
        "topic_slide_map": inputs.topic_slide_map,
        "slide_images": [os.path.basename(p) for p in inputs.slide_images],
        "pptx_name": pptx_name,
        "config": {
            "voice": settings.kokoro_voice,
            "lang": settings.kokoro_lang,
            "fps": settings.video_fps,
            "max_workers": settings.video_max_workers,
        },
    }


def _video_kwargs(
    slide_images: list[str],
    topic_slide_map: dict[str, list[int]] | None = None,
) -> dict:
    """Build keyword arguments for ``build_videos()`` based on current provider."""
    if settings.video_provider == "kokoro":
        return {
            "provider": "kokoro",
            "api_key": "",
            "avatar_id": "",
            "voice_id": "",
            "slide_images": slide_images,
            "topic_slide_map": topic_slide_map,
            "kokoro_voice": settings.kokoro_voice,
            "kokoro_lang": settings.kokoro_lang,
            "video_fps": settings.video_fps,
            "max_workers": settings.video_max_workers,
        }
    return {
        "provider": settings.video_provider,
        "api_key": settings.heygen_api_key,
        "avatar_id": settings.heygen_avatar_id,
        "voice_id": settings.heygen_voice_id,
        "emotion": settings.video_avatar_emotion,
        "speed": settings.video_avatar_speed,
        "max_workers": settings.video_max_workers,
    }


# ---------------------------------------------------------------------------
# Slide image export
# ---------------------------------------------------------------------------


def _collect_slide_sources(state, ppt_path):
    """Collect candidate slide sources in priority order."""
    sources = []
    if ppt_path and os.path.exists(ppt_path):
        sources.append(ppt_path)
    state_ppt = state.get("ppt_path", "")
    if state_ppt and os.path.exists(state_ppt) and state_ppt != ppt_path:
        sources.append(state_ppt)
    file_paths = state.get("file_paths", [])
    if file_paths:
        src = file_paths[0]
        ext = os.path.splitext(src)[1].lower()
        if ext in (".pdf", ".pptx") and src not in sources:
            sources.append(src)
    return sources


def _get_slide_images(
    state: PipelineState,
    video_dir: str,
    ppt_path: str | None = None,
) -> list[str]:
    """Export slide images for Kokoro video composition.

    Args:
        state: Pipeline state (used as fallback for file_paths).
        video_dir: Directory for video output (slide_images/ created inside).
        ppt_path: Explicit path to generated PPT -- preferred source.

    Returns the slide image paths if provider is kokoro, otherwise [].
    """
    if settings.video_provider != "kokoro":
        return []

    slide_img_dir = os.path.join(video_dir, "slide_images")
    dpi = settings.slide_export_dpi
    sources = _collect_slide_sources(state, ppt_path)

    for src in sources:
        try:
            logger.info("Exporting slide images from: %s", src)
            return export_slides_as_images(src, slide_img_dir, dpi=dpi)
        except (FileNotFoundError, RuntimeError):
            logger.warning("LibreOffice not available for slide export — deferring to remote service")
            return []
        except OSError:
            logger.warning("Slide export failed for %s", src, exc_info=True)
            continue

    logger.info("No slide source available — video will have no slide images")
    return []


# ---------------------------------------------------------------------------
# ChromaDB result caching
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
# Module validation and generation
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


def _invoke_with_retry(llm, prompt, name, model_label, severity):
    """Invoke LLM with validation retry loop.

    Returns the first valid response, or the last best-effort response
    after ``_MAX_MODULE_RETRIES`` retries.
    """
    best_result = None
    for attempt in range(_MAX_MODULE_RETRIES + 1):
        response = llm.invoke(prompt, config={"run_name": f"generate_{name}"})
        content = response.content
        is_valid, issues = _validate_module(content, name)

        if is_valid:
            logger.info("  %s: done — %d chars (%s, severity=%s)", name, len(content), model_label, severity)
            return content

        best_result = content
        if attempt < _MAX_MODULE_RETRIES:
            logger.info("  %s: validation failed (%s), retrying (%d/%d)...", name, ", ".join(issues), attempt + 1, _MAX_MODULE_RETRIES)
        else:
            logger.warning("  %s: validation failed after %d retries (%s), using best-effort", name, _MAX_MODULE_RETRIES, ", ".join(issues))

    return best_result


def _generate_module(i, topic, total, ctx, prompt_template=None):
    """Generate a single learning module with severity-based model routing and validation retry.

    Args:
        i: Zero-based topic index.
        topic: Topic dict with name, description, key_techniques.
        total: Total number of topics (for logging).
        ctx: _GenerateCtx with chroma_cache, llm_premium, llm_mini, curriculum_scope, gap_lookup.
        prompt_template: Optional custom prompt template for eval variant testing.
    """
    name = topic["name"]
    desc = topic.get("description", "")
    techniques = topic.get("key_techniques", [])
    logger.info("Module %d/%d: %s", i + 1, total, name)

    cached = ctx.chroma_cache[name]
    gap_data = ctx.gap_lookup.get(name, {})
    gap_text = json.dumps(gap_data, indent=2) if gap_data else "No gap analysis available."
    severity = gap_data.get("severity", "moderate")

    # Severity-based model routing: critical gaps get the best model
    llm = ctx.llm_premium if severity == "critical" else ctx.llm_mini
    model_label = "premium" if severity == "critical" else "mini"

    template = prompt_template or GENERATE_MODULE
    prompt = template.format(
        topic_name=name,
        topic_description=desc,
        key_techniques=", ".join(techniques) if techniques else "Not specified",
        curriculum_scope=ctx.curriculum_scope,
        curriculum_chunks=cached["curriculum_text"],
        research_chunks=cached["research_text"],
        gap_analysis=gap_text,
    )

    return _invoke_with_retry(llm, prompt, name, model_label, severity)


# ---------------------------------------------------------------------------
# Script helpers — fallback path
# ---------------------------------------------------------------------------


def _convert_to_script(topic_name, module_md, chroma_cache, llm_script):
    """Convert a markdown module into a spoken-word video script (fallback path)."""
    logger.info("Converting module to script: %s", topic_name)

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
    logger.info("  %s: ready — %d chars, %d words (~%d-%d min)", topic_name, len(script), word_count, word_count // 150, word_count // 120)
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
    for i, (topic, script) in enumerate(zip(topics, scripts, strict=True)):
        slug = _slugify(topic["name"])
        filename = f"{i + 1:02d}_{slug}{suffix}.txt"
        path = os.path.join(scripts_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        paths.append(path)
        logger.info("  Saved: %s", path)
    return paths


def _generate_scripts(ctx, video_limit):
    """Generate video scripts from markdown modules for the first N topics (fallback path)."""
    video_topics = ctx.topics[:video_limit]
    video_modules = ctx.modules_md[:video_limit]

    logger.info("Generating scripts for %d topics (prototype limit)...", video_limit)

    llm_script = get_llm("premium", temperature=settings.temp_creative)
    scripts = [None] * video_limit
    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _convert_to_script, video_topics[i]["name"], video_modules[i], ctx.chroma_cache, llm_script
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
                "stat": None,
                "stat_label": "Data unavailable — research data could not be retrieved",
                "context": f"Building practical {topic_name.lower()} skills complements your coursework and strengthens your professional profile.",
                "supporting_points": [f"Growing demand for {first_gap}", "Industry adoption accelerating", "Skills shortage in the market"],
                "source": "Fallback — no research data available",
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
# Hook variety enforcement
# ---------------------------------------------------------------------------


def _detect_hook_type(script_text):
    """Detect which hook type a script uses based on keyword heuristics.

    Only checks the first 300 chars because hooks always appear at the top
    of a video script (the opening line/paragraph).
    """
    lower = script_text[:300].lower()
    for hook_type, keywords in _HOOK_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return hook_type
    return "unknown"


def _get_hook_guidance(used_hooks, lock):
    """Generate hook guidance that emphasizes unused hook types.

    Thread-safe: uses a lock because multiple script-generation threads
    read and append to the shared ``used_hooks`` list concurrently.
    """
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
# PPT parallel structuring
# ---------------------------------------------------------------------------


def _structure_single_topic_slide(topic, module_md, gap_data, ctx, prompt_template=None):
    """Structure one topic's PPT slide data via LLM.

    Args:
        topic: Topic dict with name.
        module_md: Markdown content for this topic.
        gap_data: Gap analysis dict for this topic.
        ctx: _GenerateCtx with llm_mini and chroma_cache.
        prompt_template: Optional custom prompt template for eval variant testing.
    """
    name = topic["name"]
    research_text = ctx.chroma_cache.get(name, {}).get("research_text", "")
    template = prompt_template or STRUCTURE_SINGLE_TOPIC_SLIDE
    prompt = template.format(
        topic_name=name,
        module_content=module_md,
        gap_analysis_json=json.dumps(gap_data, indent=2) if gap_data else "{}",
        research_chunks=research_text or "No raw research data available.",
    )
    response = ctx.llm_mini.invoke(
        prompt,
        config={"run_name": f"structure_slide_{name}"},
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse slide JSON for %s, using fallback", name)
        return None


def _generate_executive_summary(topics, gap_summary, curriculum_scope, llm_nano):
    """Generate executive summary from aggregated gap data."""
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
        logger.warning("Failed to parse executive summary JSON")
        return None


def _structure_slides_parallel(ctx):
    """Structure PPT slide data in parallel: per-topic slides + executive summary.

    Falls back to monolithic STRUCTURE_GAP_SLIDES if parallel approach fails.
    """
    total = len(ctx.topics)
    llm_nano = get_llm("nano")

    # Per-topic slides in parallel
    topic_slides = [None] * total
    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(
                _structure_single_topic_slide,
                ctx.topics[i], ctx.modules_md[i],
                ctx.gap_lookup.get(ctx.topics[i]["name"], {}),
                ctx,
            ): i
            for i in range(total)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            topic_slides[idx] = future.result()

    # Executive summary
    exec_summary = _generate_executive_summary(ctx.topics, ctx.gap_summary, ctx.curriculum_scope, llm_nano)

    # Check for failures — if any topic slide failed, fall back
    if any(ts is None for ts in topic_slides) or exec_summary is None:
        logger.info("Parallel PPT structuring had failures, falling back to monolithic approach...")
        return None

    # Assemble full slide_data
    return {
        "presentation_title": ctx.curriculum_scope,
        "executive_summary": exec_summary,
        "topic_slides": topic_slides,
        "recommendations_summary": [],
    }


# ---------------------------------------------------------------------------
# PPT-aligned script generation with filtered context and hook variety
# ---------------------------------------------------------------------------


def _generate_script_for_topic(idx, topic_slide, ctx, prompt_template=None):
    """Generate one video script aligned to one PPT topic slide.

    Receives ONLY its own topic's module content and gap data (filtered context).
    This per-topic filtering prevents cross-topic contamination in scripts.

    Args:
        idx: Zero-based topic index.
        topic_slide: Structured slide dict for this topic.
        ctx: _ScriptCtx with gen (_GenerateCtx), llm_script, used_hooks, hooks_lock.
        prompt_template: Optional custom prompt template for eval variant testing.
    """
    topic_name = topic_slide.get("topic_name", "Unknown")
    severity = topic_slide.get("severity", "moderate")
    curriculum_anchor = topic_slide.get("curriculum_anchor", "Covered in coursework.")
    misconception = topic_slide.get("misconception", {})

    logger.info("Topic %d: %s — generating PPT-aligned script...", idx + 1, topic_name)

    # Use cached ChromaDB results
    cached = ctx.gen.chroma_cache.get(topic_name, {})
    curriculum_text = cached.get("curriculum_text", "No curriculum content available.")
    research_text = cached.get("research_text", "No research content available.")
    gap_data = ctx.gen.gap_lookup.get(topic_name, {})
    topic_module_md = ctx.gen.topic_modules_map.get(topic_name, "")

    # Hook variety guidance
    hook_guidance = _get_hook_guidance(ctx.used_hooks, ctx.hooks_lock)

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
        misconception_wrong=misconception.get("wrong", "") or "No specific misconception identified.",
        misconception_right=misconception.get("right", "") or "Refer to the gap concepts above for the correct understanding.",
        hook_guidance=hook_guidance,
    )
    response = ctx.llm_script.invoke(prompt, config={"run_name": f"script_slide_{topic_name}"})
    script = response.content.strip()

    # Track which hook was used
    hook_type = _detect_hook_type(script)
    with ctx.hooks_lock:
        ctx.used_hooks.append(hook_type)

    word_count = len(script.split())
    logger.info("  %s: ready — %d chars, %d words, hook=%s", topic_name, len(script), word_count, hook_type)
    return script


def _generate_scripts_from_slides(ctx, slide_data, video_limit):
    """Generate per-topic video scripts aligned to PPT topic slides.

    Each topic receives ONLY its own module content and gap data (filtered context).
    Returns (video_topics, scripts) tuple compatible with build_videos.
    """
    topic_slides = slide_data.get("topic_slides", [])[:video_limit]
    total = len(topic_slides)
    logger.info("Generating %d PPT-aligned scripts (limit: %d)...", total, video_limit)

    llm_script = get_llm("premium", temperature=settings.temp_creative)
    scripts = [None] * total
    video_topics = [{"name": ts.get("topic_name", "Unknown")} for ts in topic_slides]

    # Thread-safe hook tracking
    script_ctx = _ScriptCtx(ctx, llm_script, [], threading.Lock())

    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(_generate_script_for_topic, i, topic_slides[i], script_ctx): i
            for i in range(total)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            scripts[idx] = future.result()

    return video_topics, scripts


# ---------------------------------------------------------------------------
# PPT monolithic fallback
# ---------------------------------------------------------------------------


def _ppt_monolithic_fallback(ctx):
    """Fall back to monolithic PPT structuring when parallel structuring fails.

    Sends all modules and gap data in a single LLM call. Returns parsed
    slide data dict, or fallback placeholder data if parsing also fails.
    """
    llm_ppt = get_llm("mini")
    total = len(ctx.topics)
    modules_content = "\n\n---\n\n".join(
        f"### {ctx.topics[i]['name']}\n{md}" for i, md in enumerate(ctx.modules_md)
    )
    ppt_prompt = STRUCTURE_GAP_SLIDES.format(
        curriculum_scope=ctx.curriculum_scope,
        topic_count=total,
        modules_content=modules_content,
        gap_summary_json=json.dumps(ctx.gap_summary, indent=2),
    )
    ppt_response = llm_ppt.invoke(
        ppt_prompt,
        config={"run_name": "structure_gap_slides"},
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(ppt_response.content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse monolithic slide JSON, using fallback")
        return _build_fallback_slide_data(ctx.gap_summary, ctx.curriculum_scope)


# ---------------------------------------------------------------------------
# generate_node — extracted helpers
# ---------------------------------------------------------------------------


def _init_generate_ctx(state):
    """Initialize shared generate context from pipeline state."""
    ctx = _GenerateCtx()
    ctx.topics = state["topics"]
    ctx.curriculum_scope = state.get("curriculum_scope", "")
    ctx.gap_summary = state.get("gap_summary", [])
    ctx.formats = [
        f.strip()
        for f in state.get("output_formats", settings.output_formats).split(",")
        if f.strip()
    ]
    ctx.gap_lookup = {g.get("topic", ""): g for g in ctx.gap_summary}
    store = ChromaStore(settings.chroma_persist_dir)
    ctx.chroma_cache = _build_chroma_cache(store, ctx.topics)
    ctx.llm_premium = get_llm("premium", temperature=settings.temp_structured)
    ctx.llm_mini = get_llm("mini")
    ctx.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ctx.modules_md = None
    ctx.topic_modules_map = None
    ctx.slide_data = None
    ctx.ppt_path = None
    ctx.topic_slide_map = None
    return ctx


def _generate_all_modules(ctx):
    """Generate all markdown modules in parallel."""
    total = len(ctx.topics)
    modules_md = [None] * total
    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_idx = {
            executor.submit(_generate_module, i, topic, total, ctx): i
            for i, topic in enumerate(ctx.topics)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                modules_md[idx] = future.result()
            except PipelineCancelledError:
                raise
            except Exception as exc:
                topic_name = ctx.topics[idx]["name"]
                logger.exception("Module generation failed for '%s'", topic_name)
                modules_md[idx] = f"## {topic_name}\n\n*Module generation failed: {exc}*"

    ctx.modules_md = modules_md
    ctx.topic_modules_map = {
        t["name"]: m for t, m in zip(ctx.topics, modules_md, strict=True)
    }


def _build_pdf_and_ppt(ctx, result):
    """Build PDF and/or PPT outputs based on requested formats.

    Sets ctx.slide_data, ctx.ppt_path, ctx.topic_slide_map as side effects.
    """
    needs_pdf = "pdf" in ctx.formats
    needs_ppt = "ppt" in ctx.formats and ctx.gap_summary

    if needs_pdf and needs_ppt:
        _build_pdf_ppt_parallel(ctx, result)
        return

    if needs_pdf:
        _build_pdf_only(ctx, result)

    if needs_ppt:
        _build_ppt_only(ctx, result)
    elif "ppt" in ctx.formats:
        logger.info("Skipping PPT — no gap data available")


def _build_pdf_ppt_parallel(ctx, result):
    """Run PDF build and PPT structuring concurrently."""
    pdf_path = os.path.join("outputs", f"{ctx.timestamp}_learning_guide.pdf")
    with ThreadPoolExecutor(max_workers=2) as executor:
        pdf_future = executor.submit(
            build_pdf,
            title="Market-Enriched Learning Guide",
            topics=ctx.topics,
            modules_md=ctx.modules_md,
            output_path=pdf_path,
        )
        ppt_future = executor.submit(_structure_slides_parallel, ctx)
        pdf_future.result()
        logger.info("PDF written to %s", pdf_path)
        result["pdf_path"] = pdf_path
        ctx.slide_data = ppt_future.result()

    if ctx.slide_data is None:
        logger.info("Falling back to monolithic PPT structuring...")
        ctx.slide_data = _ppt_monolithic_fallback(ctx)

    ctx.ppt_path = os.path.join("outputs", f"{ctx.timestamp}_gap_analysis.pptx")
    _, ctx.topic_slide_map = build_gap_ppt(slide_data=ctx.slide_data, output_path=ctx.ppt_path)
    logger.info("PPT written to %s", ctx.ppt_path)
    result["ppt_path"] = ctx.ppt_path


def _build_pdf_only(ctx, result):
    """Build PDF output only."""
    pdf_path = os.path.join("outputs", f"{ctx.timestamp}_learning_guide.pdf")
    build_pdf(
        title="Market-Enriched Learning Guide",
        topics=ctx.topics,
        modules_md=ctx.modules_md,
        output_path=pdf_path,
    )
    logger.info("PDF written to %s", pdf_path)
    result["pdf_path"] = pdf_path


def _build_ppt_only(ctx, result):
    """Build PPT output only."""
    logger.info("Structuring slides from PDF content + gap analysis...")
    ctx.slide_data = _structure_slides_parallel(ctx)
    if ctx.slide_data is None:
        logger.info("Falling back to monolithic PPT structuring...")
        ctx.slide_data = _ppt_monolithic_fallback(ctx)

    ctx.ppt_path = os.path.join("outputs", f"{ctx.timestamp}_gap_analysis.pptx")
    _, ctx.topic_slide_map = build_gap_ppt(slide_data=ctx.slide_data, output_path=ctx.ppt_path)
    logger.info("PPT written to %s", ctx.ppt_path)
    result["ppt_path"] = ctx.ppt_path


def _handle_scripts_videos(state, ctx, result):
    """Generate scripts and/or videos from structured content."""
    if "script" not in ctx.formats and "video" not in ctx.formats:
        return

    video_dir = os.path.join("outputs", f"{ctx.timestamp}_videos")
    scripts_dir = os.path.join(video_dir, "scripts")
    video_limit = min(settings.video_topic_limit, len(ctx.topics))

    if ctx.slide_data is not None:
        _handle_ppt_aligned_path(state, ctx, video_dir, scripts_dir, video_limit, result)
    else:
        _handle_fallback_path(state, ctx, video_dir, scripts_dir, video_limit, result)


def _handle_ppt_aligned_path(  # noqa: PLR0913
    state, ctx, video_dir, scripts_dir, video_limit, result,
):
    """Handle PPT-aligned script generation and optional video rendering."""
    video_topics, scripts = _generate_scripts_from_slides(ctx, ctx.slide_data, video_limit)
    _save_scripts(video_topics, scripts, scripts_dir, slide_aligned=True)
    logger.info("%d PPT-aligned scripts saved to %s", len(scripts), scripts_dir)
    result["video_dir"] = video_dir

    if "video" in ctx.formats:
        _render_videos(state, ctx, video_topics, scripts, video_dir, result)


def _handle_fallback_path(  # noqa: PLR0913
    state, ctx, video_dir, scripts_dir, video_limit, result,
):
    """Handle per-module script generation and optional video rendering."""
    video_topics, scripts = _generate_scripts(ctx, video_limit)
    _save_scripts(video_topics, scripts, scripts_dir)
    logger.info("%d per-module scripts saved to %s", video_limit, scripts_dir)
    result["video_dir"] = video_dir

    if "video" in ctx.formats:
        _render_videos(state, ctx, video_topics, scripts, video_dir, result)


def _render_videos(  # noqa: PLR0913
    state, ctx, video_topics, scripts, video_dir, result,
):
    """Export slide images and dispatch video generation."""
    logger.info("Generating %d videos...", len(scripts))
    slide_images = _get_slide_images(state, video_dir, ppt_path=ctx.ppt_path)
    result["slide_images"] = slide_images
    vid_inputs = _VideoJobInputs(
        video_topics, scripts, video_dir, slide_images, ctx.topic_slide_map, ctx.ppt_path,
    )
    _build_videos_dispatch(state, vid_inputs)
    logger.info("Videos saved to %s", video_dir)


def _merge_slide_data(raw_outputs, slide_data):
    """Merge PPT slide data into raw outputs dict."""
    for ts in slide_data.get("topic_slides", []):
        name = ts.get("topic_name", "")
        if name in raw_outputs:
            raw_outputs[name]["ppt_json"] = ts
    raw_outputs["_slide_data"] = slide_data


def _save_raw_outputs(ctx):
    """Save raw pipeline outputs as JSON sidecar for eval framework."""
    raw_outputs_path = os.path.join("outputs", f"{ctx.timestamp}_raw_outputs.json")
    raw_outputs = {
        topic["name"]: {"module_md": ctx.modules_md[i] or ""}
        for i, topic in enumerate(ctx.topics)
    }
    if ctx.slide_data is not None:
        _merge_slide_data(raw_outputs, ctx.slide_data)
    try:
        with open(raw_outputs_path, "w", encoding="utf-8") as f:
            json.dump(raw_outputs, f, indent=2, ensure_ascii=False)
        logger.info("Raw outputs saved to %s", raw_outputs_path)
    except Exception:
        logger.exception("Failed to save raw outputs")


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
    logger.info("Starting generation...")
    os.makedirs("outputs", exist_ok=True)

    ctx = _init_generate_ctx(state)
    _generate_all_modules(ctx)

    result = {"current_stage": "complete"}
    _build_pdf_and_ppt(ctx, result)
    _handle_scripts_videos(state, ctx, result)
    _save_raw_outputs(ctx)

    result["modules_md"] = ctx.modules_md
    return result
