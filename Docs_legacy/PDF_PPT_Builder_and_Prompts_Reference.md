> **DEPRECATED** — This file has been superseded by the new documentation site at `docs/`. See `docs/services/` (multiple pages: `pdf-builder.md`, `ppt-builder.md`, and `agents/prompts.md`) for the current version.
>
> This file is kept for reference only and will be removed in a future cleanup.

---

# PDF & PPT Builder and Prompts Reference

Complete technical reference for the CR8 output generation system — PDF learning guides, PowerPoint teaching presentations, video scripts, and the prompt system that drives them.

---

## Architecture Overview

```
Tavily Web Search → ChromaDB Research Collection
                          ↓
Prompts (generate.py, ppt.py, video.py)
  ├── Ingest curriculum + industry research
  ├── Generate JSON for slides, modules, scripts
  └── Output grounded in research (no hallucination)
                          ↓
Builders (pdf_builder.py, ppt_builder.py)
  ├── Parse JSON/Markdown output
  ├── Render visuals (matplotlib charts, diagrams)
  └── Generate .pdf and .pptx files
                          ↓
Evals (structural checks + DeepSeek judge)
  ├── Layer 1: Validate JSON structure (free)
  └── Layer 2: Score content quality (~$0.02/run)
```

**Generation chain**: `modules_md → PDF (ground truth) → PPT (structured around PDF) → Video Script (one section per slide) → Video (HeyGen)`

---

## 1. PDF Builder (`backend/services/pdf_builder.py`)

### Purpose

Generates professional A4 PDF learning guides using `fpdf2`. Each PDF is a multi-chapter document with one chapter per topic/module, rendered in the CR8 "Midnight Teal" design language.

### Design System

| Element | Value |
|---------|-------|
| **Page size** | A4 (210 x 297 mm) |
| **Margins** | 25mm left/right |
| **Heading font** | Times (serif) — matches Georgia in PPT |
| **Body font** | Helvetica (sans) — matches Calibri in PPT |
| **Library** | `fpdf2` |

**Colour Palette** (RGB tuples for fpdf2):

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| Deep Navy | `#0D1B2A` | (13, 27, 42) | Cover bg, chapter titles |
| Teal | `#1B998B` | (27, 153, 139) | Accent lines, highlights |
| Warm Gold | `#F4B942` | (244, 185, 66) | Callout markers |
| Off White | `#F7F7F2` | (247, 247, 242) | Light backgrounds |
| Charcoal | `#2D3436` | (45, 52, 54) | Body text |
| Slate Gray | `#636E72` | (99, 110, 114) | Captions, footers |

### Page Structure

1. **Cover Page** — Full dark navy background, Times-Bold 30pt white title, teal accent lines, "Market-Enriched Learning Guide" subtitle in teal, generation date, topic count, "Powered by CR8" footer
2. **Table of Contents** — Times-Bold 22pt navy heading, teal-numbered topic entries
3. **Chapters (one per topic)** — Teal left accent bar, chapter number in teal, Times-Bold 20pt navy title, teal underline, optional slate gray italic description, markdown content rendering

### Rendering Capabilities

#### LaTeX Math Rendering
- **Inline math**: `\( expr \)` — rendered as PNG images via matplotlib, embedded inline at cursor position
- **Display math**: `\[ expr \]` — rendered as centered equation images (14pt, 200dpi)
- **Fallback**: If matplotlib fails, LaTeX is converted to readable ASCII using `_LATEX_CMD_MAP` (e.g., `\alpha` → "alpha", `\frac{a}{b}` → "a/b")
- **Implementation**: `_render_latex_to_png()`, `_embed_latex_image()`, `_render_text_with_latex()`, `_render_display_math()`

#### Rich Text Rendering
- **Bold**: `**text**` → Helvetica-Bold inline
- **Italic**: `*text*` → Helvetica-Italic inline
- **Mixed**: Handles interleaved bold/italic/plain text via `pdf.write()` calls
- **Markdown links**: `[text](url)` → flattened to "text (url)"
- **Implementation**: `_render_rich_text()`

#### Code Block Rendering
- Triple-backtick fenced code blocks detected during line processing
- Rendered in Courier 8pt on a light gray background (`#F0F0EB`)
- Auto page break if block doesn't fit
- **Implementation**: `_render_code_block()`

#### Markdown Line Rendering (`_render_markdown_line()`)
All standard markdown elements are supported:

| Element | Rendering |
|---------|-----------|
| `# H1` | Helvetica-Bold 14pt, navy, teal underline |
| `## H2` | Helvetica-Bold 13pt, navy, teal underline |
| `### H3` | Helvetica-Bold 11pt, teal |
| `#### H4+` | Helvetica-Bold 10pt, teal |
| `- bullet` | Teal dash marker + rich text body |
| `1. numbered` | Teal bold number + rich text body |
| `> blockquote` | Gold left accent bar, Helvetica-Italic 9pt slate gray |
| `---` / `***` | Teal horizontal rule |
| Display math | Centered matplotlib equation image |
| Inline HTML | Stripped (tags removed, content kept) |
| Inline code | Backticks stripped, content rendered as plain text |

#### Unicode Handling
GPT models frequently emit Unicode characters that Helvetica (latin-1) cannot render. The `_sanitize()` function replaces 17 Unicode characters:
- Smart quotes: `'` `'` `"` `"` → ASCII equivalents
- Dashes: en dash, em dash, non-breaking hyphen → `-`/`--`
- Bullets: `•` → `-`, `‣` → `>`
- Zero-width characters: ZWS, ZWNJ, ZWJ, BOM → removed
- Final fallback: `encode("latin-1", errors="replace")` for any remaining characters

### Public API

```python
def build_pdf(
    title: str,           # Document title (shown on cover)
    topics: list[dict],   # [{"name": "...", "description": "..."}]
    modules_md: list[str], # Markdown content for each topic
    output_path: str,     # Output file path
) -> None
```

---

## 2. PPT Builder (`backend/services/ppt_builder.py`)

### Purpose

Generates professional widescreen (16:9) PowerPoint presentations using `python-pptx` + `matplotlib`. The PPT **teaches** industry-relevant concepts as a seamless add-on to an existing curriculum, using assertion-evidence slide design grounded in Mayer's multimedia learning principles.

### Design System

| Element | Value |
|---------|-------|
| **Slide dimensions** | 13.333" x 7.5" (widescreen 16:9) |
| **Heading font** | Georgia (serif) |
| **Body font** | Calibri (sans) |
| **Margins** | 0.5" all sides |
| **Library** | `python-pptx`, `matplotlib`, `numpy` |

**Colour Palette** (RGBColor objects):

| Token | Hex | Usage |
|-------|-----|-------|
| Deep Navy | `#0D1B2A` | Dark backgrounds, headers |
| Teal | `#1B998B` | Accents, badges, diagrams |
| Warm Gold | `#F4B942` | Callouts, stats, section numbers |
| Off White | `#F7F7F2` | Content slide backgrounds |
| Charcoal | `#2D3436` | Body text |
| Slate Gray | `#636E72` | Captions, footers |
| Teal Tint | `#E6F5F3` | Light teal backgrounds for cards |
| Gold Tint | `#FEF6E2` | Light gold backgrounds for callouts |

**Priority / Severity Mapping**:

| Internal severity | User-facing label | Colour |
|---|---|---|
| `critical` | ESSENTIAL | Teal |
| `moderate` | RECOMMENDED | Gold |
| `minor` | SUPPLEMENTARY | Slate Gray |

### Slide Sequence

The presentation follows this fixed structure:

| # | Slide Type | Background | Key Elements |
|---|------------|------------|-------------|
| 1 | **Title Slide** | Deep Navy | Georgia 40pt white title, teal accent line, CR8 branding |
| 2 | **Course Overview** | Off White | 5 KPI stat cards (Concepts, Topics, Essential, Recommended, Supplementary), "What You'll Learn" section, key topics list |
| 3 | **Coverage Radar Chart** | Off White | Matplotlib polar chart: teal "Your Course" vs gold "Industry Standard", auto-generated from topic_scores |
| 4 | **Topics at a Glance** | Off White | Scorecard table with topic names, coloured severity badges, concept counts; paginated (10 per slide) |
| 5 | **Section Divider** | Deep Navy | Gold section number (72pt), Georgia white title (32pt), teal accent line |
| 6–N | **Per-Topic Group** (3 slides each): | | |
| | a. Topic Teaching | Off White | Assertion title (Georgia 24pt), importance badge, curriculum anchor (italic), concept cards with diagrams, misconception wrong/right boxes |
| | b. Market Intelligence | Split (Navy/Off White) | Left: gold "MARKET SIGNAL" badge, key finding (Georgia 20pt white), stat number (52pt gold); Right: "What This Means For You", context, evidence points, source citation |
| | c. Quiz / Reflection | Off White | Teal header bar, question (Georgia 22pt), A-D options with teal circles, gold reflection prompt |
| N+1 | **Section Divider** | Deep Navy | Section 2: "What to Learn Next" |
| N+2 | **Recommendations** | Off White | Process flow diagram (Review → Plan → Practice → Apply), prioritized recommendation cards with coloured stripes |
| N+3 | **Closing** | Deep Navy | "Key Takeaways" (gold Georgia 36pt), numbered points with teal circles |

### Diagram Renderers

Three native diagram types, all built with `python-pptx` shapes (no external images):

#### Process Flow (`_add_process_flow_diagram`)
- Left-to-right sequence of rounded rectangles connected by right-arrow shapes
- Teal fill with white bold 9pt text, slate gray arrows
- Adapts node width based on count and available space
- Configurable node colours via `node_colors` parameter

#### Comparison (`_add_comparison_diagram`)
- Two-column layout: "Curriculum" (slate gray header) vs "Industry" (teal header)
- Items listed below each header, capped at 4 items
- Adaptive row spacing based on available height

#### Concept Map (`_add_concept_map_diagram`)
- Tree diagram: center node (deep navy) with trunk → spine → branch → satellite nodes (teal)
- Uses horizontal trunk from center to vertical spine, then branches to each satellite
- Satellites stacked vertically, capped at 5
- All connectors are teal 2pt rectangles (not native lines)

### Radar Chart (`_generate_radar_chart`)
- Matplotlib polar plot comparing curriculum_score vs industry_requirement per topic
- Teal filled polygon for "Your Course", gold for "Industry Standard"
- Labels truncated at 18 characters
- Transparent background, 150dpi PNG embedded via `slide.shapes.add_picture()`

### Helper Functions

| Function | Purpose |
|----------|---------|
| `_set_slide_bg()` | Set solid background colour |
| `_add_textbox()` | Configurable text box (font, size, colour, alignment, word wrap) |
| `_add_rect()` | Rectangle with optional fill/line |
| `_add_rounded_rect()` | Rounded rectangle (badges, cards) |
| `_add_badge()` | Coloured rounded-rect badge with white bold text |
| `_add_oval()` | Circle/oval shape (bullets, quiz letters) |
| `_add_teal_accent_line()` | Horizontal teal 4pt accent line |
| `_add_teal_accent_bar()` | Vertical teal 4pt accent bar |
| `_add_separator_line()` | Thin slate gray horizontal line |
| `_add_header_bar()` | Deep navy header bar with Georgia title |
| `_add_multiline_textbox()` | Multi-paragraph text box |
| `_add_footer()` | "Powered by CR8 | date" footer |
| `_severity_color()` | Map severity → colour |
| `_severity_label()` | Map severity → user-facing label |
| `_impact_color()` | Map impact → colour |
| `_strip_latex()` | Strip LaTeX from text (imported from pdf_builder) |

### Public API

```python
def build_gap_ppt(
    slide_data: dict,     # Structured JSON from LLM (see PPT prompt output schema)
    output_path: str,     # Output file path
) -> str                  # Returns output_path
```

---

## 3. Prompt System

### 3.1 Module Generation Prompt (`backend/prompts/generate.py`)

**Prompt**: `GENERATE_MODULE`
**Model**: GPT-5.1 (critical topics) / GPT-5-mini (moderate/minor topics)
**Temperature**: 0.3

**Input variables**:
- `{curriculum_scope}` — Domain scope (e.g., "NLP", "Machine Learning")
- `{topic_name}` — Specific topic
- `{topic_description}` — Brief description
- `{key_techniques}` — Techniques from curriculum
- `{curriculum_chunks}` — Retrieved curriculum content (ChromaDB)
- `{research_chunks}` — Industry research data (Tavily web search)
- `{gap_analysis}` — Gap analysis JSON from research agent

**Output**: Markdown document with exactly these sections (in order):

| Section | Content | Key rules |
|---------|---------|-----------|
| `## Module Overview` | 3-5 sentence preview | Real-world problem/scenario, industry relevance, what student gains |
| `## Learning Objectives` | 3-5 Bloom's taxonomy objectives | Each MUST end with `(Curriculum)` or `(Gap)` tag; at least one of each |
| `## Curriculum Coverage` | What the course teaches | Draw ONLY from curriculum content; end with 2-3 quick-check questions |
| `## Identified Gaps` | What's missing | Frame as opportunities; priority tags: (Critical), (Important), (Nice-to-have) |
| `## Core Content` | Main teaching section | `### What You Need to Learn` + `### Common Misconceptions`; do NOT repeat curriculum |
| `## Industry Context` | Real-world application | 2-3 job titles, one detailed use case, employer requirements |
| `## Practice & Review` | `### Quick Check` + `### Apply It` | Mix of recall, conceptual, and application questions |
| `## Key Takeaways` | 7-10 bullet points | Prefixed: `Curriculum:`, `Gap:`, `Integration:` |
| `## Reflection` | 3 metacognitive prompts | Fixed format with self-assessment questions |
| `## Further Reading` | 3-5 curated resources | Only URLs from research data; type + difficulty tags |

**Validation**: Generated modules checked for required sections (`## Module Overview`, `## Learning Objectives`, `## Core Content`, `## Key Takeaways`) and minimum 2000 characters. Failed modules retried up to 2 times.

---

### 3.2 PPT Prompts (`backend/prompts/ppt.py`)

Three prompt variants for different PPT generation modes:

#### `STRUCTURE_GAP_SLIDES` (Full Presentation)
**Model**: GPT-5.1 (original monolithic mode, now replaced by per-topic)
**Input variables**: `{curriculum_scope}`, `{topic_count}`, `{modules_content}`, `{gap_summary_json}`

**Output JSON schema**:
```json
{
  "presentation_title": "...",
  "executive_summary": {
    "total_gaps_found": int,
    "topics_analyzed": int,
    "critical_count": int,
    "moderate_count": int,
    "minor_count": int,
    "critical_gaps": ["..."],
    "overall_assessment": "...",
    "topic_scores": [
      {"topic": "...", "curriculum_score": int, "industry_requirement": int}
    ]
  },
  "topic_slides": [
    {
      "topic_name": "...",
      "slide_title": "Full teaching assertion (max 12 words)",
      "severity": "critical|moderate|minor",
      "curriculum_anchor": "You already know...",
      "gap_concepts": [
        {
          "concept_name": "...",
          "definition": "...",
          "why_it_matters": "...",
          "how_it_works": "...",
          "impact": "high|medium|low",
          "diagram_type": "process_flow|comparison|concept_map|none",
          "diagram_data": {"nodes": [...], "labels": [...]}
        }
      ],
      "misconception": {"wrong": "...", "right": "..."},
      "quiz": {
        "question": "...",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "correct": "B",
        "reflection_prompt": "..."
      },
      "market_signal": {
        "signal": "...",
        "stat": "85%",
        "stat_label": "...",
        "context": "...",
        "supporting_points": ["...", "...", "..."],
        "source": "..."
      },
      "top_recommendations": ["..."]
    }
  ],
  "recommendations_summary": [
    {"priority": "high|medium|low", "action": "...", "topics_affected": ["..."]}
  ]
}
```

**Key rules**:
1. Slide titles must be full teaching assertions (assertion-evidence format), not short labels
2. Curriculum anchor must start with "You already know..."
3. 1-3 gap_concepts per topic; most important MUST have a diagram
4. Diagram data: 3-6 nodes with 2-5 word text each
5. NEVER use the word "gap" in any slide content — frame as learning opportunities
6. Every topic MUST have quiz and market_signal objects
7. Topic slides follow same order as PDF chapters

#### `STRUCTURE_SINGLE_TOPIC_SLIDE` (Per-Topic Mode)
**Model**: GPT-5-mini
**Purpose**: Generates one topic slide at a time (replaces monolithic call for better quality + lower per-call tokens)

**Input variables**: `{topic_name}`, `{module_content}`, `{gap_analysis_json}`, `{research_chunks}`

**Output**: Same schema as a single `topic_slides` entry above.

**Additional rule**: `market_signal.stat` MUST be a real number extracted from `{research_chunks}` — no invented statistics.

#### `STRUCTURE_EXECUTIVE_SUMMARY` (Overview Slide)
**Model**: GPT-5-nano
**Purpose**: Generates only the executive summary data (stats, scores, assessment) for the overview slides.

**Input variables**: `{curriculum_scope}`, `{topics_analyzed}`, `{total_gaps_found}`, `{critical_count}`, `{moderate_count}`, `{minor_count}`, `{topic_severities_json}`, `{critical_gaps_sample}`

**Output**: The `executive_summary` portion of the full schema.

---

### 3.3 Video Script Prompts (`backend/prompts/video.py`)

#### `HOOK_EXAMPLES`
Shared guidance for hook type selection:
1. **Curiosity Question**: "What if I told you..."
2. **Scenario**: "Imagine you're on your first day as a [role]..."
3. **Statistic**: "80% of job postings require Y..."
4. **Misconception**: "Most students think X works like Y..."
5. **Value Promise**: "In the next 3 minutes, you'll learn..."

Hook variety is enforced via thread-safe tracking across scripts.

#### `MODULE_TO_SCRIPT` (Standalone Module Script)
**Model**: GPT-5.1 (temperature 0.55)
**Purpose**: Generates a video script from a single learning module (fallback when PPT is not selected).

**Input variables**: `{topic_name}`, `{module_content}`, `{curriculum_chunks}`, `{research_chunks}`, `{hook_guidance}`

**6-Section Structure** (continuous spoken text, no labels):

| Section | Word count | Duration | Content |
|---------|-----------|----------|---------|
| Hook | 30-45 | 10-15s | Topic-specific hook |
| Anchor | 45-60 | 15-20s | Connect to prior knowledge |
| Teach the Gap | 300-450 | 2-3 min | Core teaching (definitions, examples, step-by-step) |
| Misconception | 60-90 | 20-30s | "A lot of students think... But here's the thing..." |
| Retrieval Prompt | 30-45 | 10-15s | Pause and think prompt |
| Takeaways | 60-90 | 20-30s | 3-4 key points + forward-looking close |

**Target**: 300-750 words, under 4500 characters.

#### `SCRIPT_FROM_SLIDES` (PPT-Synced Script)
**Model**: GPT-5.1 (temperature 0.55)
**Purpose**: Generates a video script synced to a specific PPT topic slide. This is the primary mode when PPT is selected.

**Input variables**: `{topic_name}`, `{severity}`, `{topic_slide_json}`, `{curriculum_chunks}`, `{research_chunks}`, `{modules_content}`, `{research_context}`, `{curriculum_anchor}`, `{misconception_wrong}`, `{misconception_right}`, `{hook_guidance}`

**6-Section Structure** (same as above, but tighter word counts):

| Section | Word count | Duration | Additional rules |
|---------|-----------|----------|-----------------|
| Hook | 25-35 | — | Severity-aware urgency |
| Anchor | 40-55 | — | Uses curriculum_anchor directly |
| Teach the Gap | 200-320 | — | Follow gap_concepts IN ORDER from PPT slide; reference diagrams |
| Misconception | 50-70 | — | Rephrase, don't read verbatim |
| Retrieval Prompt | 25-35 | — | — |
| Takeaways | 50-75 | — | — |

**Target**: 400-600 words (aim ~500), under 3800 characters.

**Key rules for both script prompts**:
1. Write ONLY spoken words — no stage directions, markdown, headers, asterisks
2. Conversational "you" language throughout
3. **Contractions are MANDATORY**: "you'll" not "you will", "it's" not "it is", etc.
4. Do NOT duplicate slide content verbatim — complement it
5. No URLs, citations, or "further reading" references
6. Single continuous text block with paragraph breaks for natural pauses

---

### 3.4 Ingest Prompts (`backend/prompts/ingest.py`)

**Model**: GPT-5-nano (temperature 0.2)

- **File summarization**: Extracts topic structure and key concepts from uploaded course materials
- **`SUMMARIZE_CHUNK`**: Summarizes a single chunk of a long file (map step)
- **`REDUCE_SUMMARIES`**: Combines chunk summaries into a single coherent summary (reduce step)
- **Map-reduce**: Files >15K characters are split into 12K chunks, each summarized independently, then combined

---

### 3.5 Research Prompt (`backend/prompts/research.py`)

**Model**: GPT-5-mini (temperature 0.3)

- Compares curriculum topics against industry requirements using Tavily web search results
- Outputs structured gap analysis JSON with `severity` field (`critical`/`moderate`/`minor`) per topic
- Severity drives model routing: critical topics → GPT-5.1, moderate/minor → GPT-5-mini

---

## 4. Evaluation Framework

### PPT Structural Checks (`backend/evals/structural/ppt_checks.py`)

Layer 1 validation — free, runs locally. Handles both full presentation and single topic slide formats. Backwards-compatible with old field names (`severity`/`gap_concepts` ↔ `importance`/`concepts`).

| Check | What it validates |
|-------|-------------------|
| `valid_json` | Input parses as valid JSON |
| `schema_complete` | Required keys present: `topic_name`, `slide_title`, `gap_concepts` or `concepts`, `severity` or `importance` |
| `severity_valid` | Values are one of: `critical`, `moderate`, `minor` |
| `diagram_data_valid` | `diagram_type` is valid; non-"none" diagrams have 3-6 nodes |
| `assertion_titles` | Slide titles have >= 5 words (assertion-evidence heuristic) |
| `slide_count_matches` | (Full presentation only) Topic count matches expected |
| `topic_scores_complete` | (Full presentation only) All topic_scores have valid 0-100 integers |

### PPT Judge (`backend/evals/judges/ppt_judge.py`)

Layer 2 semantic evaluation — uses DeepSeek-V3 (`deepseek-chat`, ~$0.02/run) via `PPT_RUBRIC` prompt for deep quality assessment of slide content, teaching effectiveness, and curriculum grounding.

---

## 5. Voice and Framing Rules

These rules apply across ALL prompts and builders:

1. **"You" voice**: Address the student directly ("You already know...", "Here's how industry applies this...")
2. **No gap language**: NEVER use "gap analysis", "what's missing", "coverage falls short" in student-facing content. JSON field names like `gap_concepts` are internal only.
3. **Positive framing**: Frame industry differences as "here's what you'll learn next" or "industry takes this further by..."
4. **Assertion-evidence titles**: Slide titles must be full teaching assertions, not short labels. "Skip-gram requires sampled objectives to scale to real-world vocabularies." NOT "Skip-gram Issues"
5. **Curriculum grounding**: All claims must be supported by curriculum content or industry research — no hallucination
6. **Mandatory contractions** (video scripts): "you'll" not "you will", "it's" not "it is"
7. **Severity-to-priority mapping**: `critical` = Essential, `moderate` = Recommended, `minor` = Supplementary

---

## 6. Model Routing Summary

| Task | Model | Temperature | Prompt |
|------|-------|-------------|--------|
| File summarization | GPT-5-nano | 0.2 | `SUMMARIZE_CHUNK` / `REDUCE_SUMMARIES` |
| Gap analysis | GPT-5-mini | 0.3 | Research prompt |
| Module generation (critical) | GPT-5.1 | 0.3 | `GENERATE_MODULE` |
| Module generation (moderate/minor) | GPT-5-mini | 0.3 | `GENERATE_MODULE` |
| PPT executive summary | GPT-5-nano | 0.2 | `STRUCTURE_EXECUTIVE_SUMMARY` |
| PPT per-topic slides | GPT-5-mini | 0.3 | `STRUCTURE_SINGLE_TOPIC_SLIDE` |
| Video scripts | GPT-5.1 | 0.55 | `MODULE_TO_SCRIPT` / `SCRIPT_FROM_SLIDES` |
| PPT evaluation (L2) | DeepSeek-V3 | — | `PPT_RUBRIC` |

---

## 7. File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `backend/services/pdf_builder.py` | 668 | PDF learning guide builder (fpdf2) |
| `backend/services/ppt_builder.py` | 1,290 | PPT teaching presentation builder (python-pptx + matplotlib) |
| `backend/prompts/generate.py` | 120 | Module generation prompt |
| `backend/prompts/ppt.py` | 218 | PPT structuring prompts (3 variants) |
| `backend/prompts/video.py` | 129 | Video script prompts (2 variants + hook examples) |
| `backend/prompts/ingest.py` | ~100 | File summarization + map-reduce prompts |
| `backend/prompts/research.py` | ~80 | Gap analysis prompt |
| `backend/evals/structural/ppt_checks.py` | 113 | PPT structural validation (L1) |
| `backend/evals/judges/ppt_judge.py` | 22 | PPT semantic judge (L2, DeepSeek-V3) |
| `backend/tests/test_pdf_builder.py` | ~150 | PDF builder test suite |

---

## 8. Dependencies

| Package | Version | Used by |
|---------|---------|---------|
| `fpdf2` | >=0.7 | PDF builder |
| `python-pptx` | >=0.6 | PPT builder |
| `matplotlib` | >=3.8 | LaTeX rendering (PDF), radar charts (PPT) |
| `numpy` | >=1.26 | Radar chart angles/data |

---

*Last updated: February 28, 2026*
