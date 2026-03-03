# Eval Architecture

The evaluation framework uses a two-layer design: **L1 structural checks** that are free and instant, and **L2 LLM judges** that provide nuanced scoring at minimal cost (~$0.02 per run).

## L1: Structural Checks

Structural checks validate format, completeness, and basic quality constraints without calling any external API. Each check returns a `CheckResult(passed: bool, message: str)`.

### Module Checks

**File**: `backend/evals/structural/module_checks.py`

| Check | Description |
|-------|-------------|
| `has_all_sections` | All required sections (Learning Objectives, Core Content, Quick Check, Key Takeaways, etc.) are present |
| `sections_in_order` | Sections appear in the expected pedagogical sequence |
| `min_length` | Module meets minimum character count threshold |
| `has_blooms_verbs` | Learning objectives use Bloom's taxonomy action verbs (analyze, evaluate, create, etc.) |
| `has_curriculum_gap_tags` | Content is properly tagged with `(Curriculum)` and `(Gap)` markers |
| `has_quick_check_answers` | Quick check questions include answer keys |
| `has_takeaway_prefixes` | Key takeaways use standardized prefix format |
| `core_content_has_subheadings` | Core content section is organized with subheadings for readability |

### Script Checks

**File**: `backend/evals/structural/script_checks.py`

| Check | Description |
|-------|-------------|
| `word_count_in_range` | Word count falls within 300-750 words (optimal for 2-5 minute videos) |
| `char_count_under_limit` | Character count stays under 3,800 (HeyGen API limit) |
| `no_markdown` | Script contains no markdown formatting (headers, bold, links, etc.) |
| `no_section_labels` | Script does not contain section labels like "Introduction:" or "Conclusion:" |
| `has_question_mark` | Script includes at least one rhetorical or engagement question |
| `uses_contractions` | Script uses contractions for natural spoken-word tone |
| `no_stage_directions` | Script does not contain stage directions like "[pause]" or "(gesture)" |

### PPT Checks

**File**: `backend/evals/structural/ppt_checks.py`

| Check | Description |
|-------|-------------|
| `valid_json` | PPT data parses as valid JSON |
| `schema_complete` | All required fields are present (title, slides, metadata) |
| `severity_valid` | Gap severity values are within the allowed range |
| `diagram_data_valid` | Diagram data structures are well-formed |
| `assertion_titles` | Slide titles follow assertion-evidence format |
| `slide_count_matches` | Number of slides matches the declared count |
| `topic_scores_complete` | All topic scores are present and within valid range |

## L2: LLM Judge

The L2 layer uses **DeepSeek-V3** (`deepseek-chat`) via the OpenAI-compatible SDK to evaluate outputs against weighted rubrics.

### Configuration

```python
# DeepSeek connection
base_url = "https://api.deepseek.com"
model = "deepseek-chat"
```

!!! note
    Requires a `DEEPSEEK_API_KEY` environment variable. Each evaluation run costs approximately $0.02.

### ModuleJudge

Evaluates learning module quality across 9 weighted criteria:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| `DOMAIN_SCOPE_FIDELITY` | 0.10 | Output stays within the declared topic/domain scope |
| `GAP_IDENTIFICATION_ACCURACY` | 0.15 | Correctly identifies gaps between curriculum and industry needs |
| `CURRICULUM_GAP_SEPARATION` | 0.10 | Clear separation between curriculum content and gap content |
| `PEDAGOGICAL_DEPTH` | 0.20 | Depth and quality of teaching material |
| `LEARNING_OBJECTIVES_QUALITY` | 0.08 | Well-formed objectives using Bloom's taxonomy |
| `INDUSTRY_CONTEXT_RELEVANCE` | 0.10 | Industry examples are current and relevant |
| `PRACTICE_ASSESSMENT_QUALITY` | 0.10 | Practice problems and assessments are effective |
| `FACTUAL_GROUNDING` | 0.12 | Claims are accurate and well-supported |
| `STRUCTURAL_COMPLETENESS` | 0.05 | All required structural elements are present |

### PPTJudge

Evaluates PowerPoint gap analysis quality across 6 criteria covering visual clarity, data accuracy, severity calibration, assertion-evidence structure, diagram effectiveness, and slide narrative flow.

### ScriptJudge

Evaluates video scripts across 7 criteria covering spoken-word naturalness, engagement hooks, pacing, content accuracy, educational value, audience appropriateness, and conclusion effectiveness.

### ConsistencyJudge

A cross-output judge that evaluates consistency between the learning module, PPT, and scripts. Checks for terminology alignment, topic coverage overlap, and narrative coherence across all pipeline outputs.

### Scoring

Each criterion is scored on a **1-5 scale**:

| Score | Meaning |
|-------|---------|
| 1 | Unacceptable - Major issues, fails to meet basic requirements |
| 2 | Below Average - Significant gaps, needs substantial revision |
| 3 | Adequate - Meets minimum requirements with room for improvement |
| 4 | Good - Solid quality, minor improvements possible |
| 5 | Excellent - Exceptional quality, no meaningful improvements needed |

The **weighted total** is computed as:

```
weighted_total = sum(score_i * weight_i for each criterion)
```

## Eval Schemas

### EvalInput

Input data for a single evaluation case:

| Field | Type | Description |
|-------|------|-------------|
| `case_id` | `str` | Unique identifier for the test case |
| `input_pdfs` | `list[str]` | Paths to input PDF files |
| `topic_name` | `str` | Topic being evaluated |
| `curriculum_scope` | `str` | Expected curriculum coverage |
| `gap_summary` | `str` | Expected gap identification summary |

### EvalResult

Result from evaluating a single output:

| Field | Type | Description |
|-------|------|-------------|
| `case_id` | `str` | Test case identifier |
| `output_type` | `str` | One of `module`, `ppt`, `script` |
| `structural_checks` | `dict[str, CheckResult]` | L1 check results |
| `criterion_scores` | `dict[str, float]` | L2 per-criterion scores (1-5) |
| `weighted_total` | `float` | L2 weighted aggregate score |

### ComparisonResult

Result from comparing two prompt variants:

| Field | Type | Description |
|-------|------|-------------|
| `variant_a` | `str` | First variant identifier (e.g., `v1`) |
| `variant_b` | `str` | Second variant identifier (e.g., `v2`) |
| `aggregate_scores` | `dict[str, float]` | Aggregate score per variant |
| `per_criterion_deltas` | `dict[str, float]` | Score difference per criterion (B - A) |
| `p_value` | `float` | Statistical significance of the difference |
| `winner` | `str` | Variant with the higher aggregate score |
