# ADR-008: Chained Output Generation (PDF, PPT, Script, Video)
<!-- Architecture Decision Record
     Place in: docs/adr/ADR-008-chained-output-generation.md
     Reference from AGENTS.md so the agent knows these exist.
     The agent reads ADRs before making structural decisions. -->

**Date:** 2026-02-01
**Status:** Accepted
**Deciders:** Shreyas Jagannath

---

## Context

CR8 generates four output formats from a single curriculum PDF upload: a learning
guide (PDF), a gap analysis presentation (PPT), spoken-word video scripts, and
narrated slide videos. These formats share the same underlying content — research
data, gap analysis, and generated learning modules — but each format has different
structural requirements.

The core tension was: should each format be generated independently from the raw
research data, or should they form a dependency chain where later formats build on
earlier ones? Independent generation would be faster (fully parallel) but risks
inconsistency — a script might reference content that does not appear in the PPT,
or the PDF might structure topics differently than the slides. For an educational
product, content consistency across formats is non-negotiable.

A decision was needed at v0.2 when Script and Video formats were added to the
pipeline alongside the existing PDF and PPT outputs.

## Decision

> We will use a chained generation strategy with markdown modules as the canonical
> content source, where PDF and PPT are built in parallel from modules, scripts
> are generated from PPT slide structure, and videos are composed from scripts
> plus PPT slide images.

The dependency graph:

```
ChromaDB + Gap Analysis
        |
        v
  modules_md (markdown)    <-- canonical content, always generated first
       / \
      /   \
     v     v
   PDF    PPT structuring   <-- parallel (both only need modules_md)
           |
           v
        slide_data
           |
           v
     Script (SCRIPT_FROM_SLIDES)  <-- depends on PPT topic_slide_json
           |
           v
     Video (TTS + ffmpeg)   <-- depends on script + slide images from PPT
```

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **A. Chained generation with modules_md as source of truth (chosen)** | Content consistency across all formats; scripts narrate exactly what is on screen; single LLM pass for content; PPT structure reused for video alignment | PPT failure blocks script+video; longer end-to-end time due to sequential dependencies; more complex orchestration |
| B. Independent generation per format | Maximum parallelism; no cascading failures; simpler per-format logic | Content drift between formats (script says X, slide shows Y); duplicate LLM calls for same content; no slide-script alignment possible |
| C. Single master document with format-specific renderers | One LLM call produces all content; renderers are pure functions; easiest to reason about | Master document schema would be enormous and brittle; no format can have unique structure (e.g., PPT quiz slides, video hooks); single point of failure |
| D. Template-based fill-in-the-blank generation | Fast; predictable output structure; low LLM cost | Rigid output; cannot adapt to varying topic complexity; poor pedagogical quality; no gap-severity-based customization |

## Consequences

**Positive:**
- Script narration is synchronized to PPT slide structure via `SCRIPT_FROM_SLIDES` prompt, which receives `topic_slide_json` directly
- Video slide images are exported from the same PPT file, so visuals and audio match
- PDF and PPT run in parallel (ThreadPoolExecutor, max_workers=2) since both only need `modules_md`
- Adding a new format only requires deciding where it attaches in the chain, not rebuilding everything
- Per-topic filtered context in scripts prevents cross-topic contamination

**Negative / Trade-offs:**
- PPT structuring failure cascades to script and video; mitigated by fallback to `MODULE_TO_SCRIPT` prompt (per-module scripts without slide alignment)
- End-to-end latency is dominated by the sequential path: modules -> PPT -> script -> TTS -> video (~34 min on benchmark)
- The `SCRIPT_FROM_SLIDES` prompt is tightly coupled to PPT slide_data schema; changes to PPT structure require script prompt updates

**Neutral:**
- The `modules_md` list (not the PDF file) is the actual canonical source; "PDF as ground truth" means PDF is the most complete textual rendering, but all formats derive from the same markdown
- Hook variety enforcement (`_get_hook_guidance`, `_detect_hook_type`) operates independently of the chain — it is a script-level concern

## Implementation Notes

- Files affected:
  - `backend/pipeline/agent_generate.py` — orchestrates the full chain in `generate_node()`
  - `backend/services/pdf_builder.py` — `build_pdf()` renders modules_md to formatted A4 PDF
  - `backend/services/ppt_builder.py` — `build_gap_ppt()` renders slide_data to PPTX, returns `topic_slide_map`
  - `backend/services/script_parser.py` — `parse_script()` splits `[SLIDE N]` markers into segments
  - `backend/services/video_builder.py` — `build_videos()` / `_build_kokoro_videos()` two-phase pipeline
  - `backend/prompts/video.py` — `SCRIPT_FROM_SLIDES` and `MODULE_TO_SCRIPT` prompt constants

- Patterns to follow:
  - Always generate `modules_md` before any format-specific output
  - PDF and PPT may run concurrently (no dependency between them)
  - Scripts must wait for `slide_data` from PPT structuring
  - Videos must wait for both scripts and slide images (exported from PPT via `export_slides_as_images`)
  - Use `_generate_scripts_from_slides()` when `slide_data` is available; fall back to `_generate_scripts()` when it is not

- Things to avoid:
  - Never generate scripts before PPT structuring completes — the `SCRIPT_FROM_SLIDES` prompt requires `topic_slide_json`
  - Never generate video scripts directly from PDF content (loses slide-level alignment)
  - Never allow formats to query ChromaDB independently for content — always go through the shared `chroma_cache` built once in `generate_node()`

## References

- `backend/pipeline/agent_generate.py` — `generate_node()` full orchestration
- `backend/prompts/video.py` — `SCRIPT_FROM_SLIDES` prompt pattern
- E2E benchmark (M&A PDF, 33 slides): Ingest 51s, Research 2m29s, Generate 2m19s, Script 14s, Video 28m21s
- ADR-001 — Three-tier video fallback (downstream consumer of this chain)
