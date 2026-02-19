# Changelog

## Unreleased — Curriculum/Gap Sections, Parallelization, Domain Scoping, and Test Hardening

**Summary**: PDF chapters now explicitly show curriculum coverage and identified gaps with tagged learning objectives and structured takeaways. Also includes major performance improvement through concurrent execution, domain-scoped prompts, enriched topic extraction, and a comprehensive PDF builder test suite.

---

### Curriculum Coverage & Gap Sections in PDF

Each generated chapter now includes two new sections and revised existing sections to clearly surface what the original slides cover and what gaps exist.

**New sections** (added before Learning Objectives):
- **Curriculum Coverage** — summarizes what the original course materials teach about the topic, drawn only from curriculum content
- **Identified Gaps** — describes gaps between curriculum and industry demands, with explanations of why each gap matters

**Revised sections**:
- **Learning Objectives** — each objective is now tagged as `(Curriculum)` or `(Gap)` to indicate whether it addresses course content or an identified gap
- **Key Takeaways** — increased to 7-10 bullets, structured in three groups: `Curriculum:` (core knowledge), `Gap:` (what to learn beyond the course), `Integration:` (how both connect in practice)

**Files changed**:
- `backend/prompts/generate.py` — complete rewrite of `GENERATE_MODULE` prompt (5 sections → 7 sections)
- `backend/pipeline/agent_generate.py` — now passes `key_techniques` from the topic dict to the prompt
- `backend/tests/test_pdf_builder.py` — added test for the new 7-section markdown format

---

### Parallelization (All Agents)

All three pipeline agents now process work concurrently using `ThreadPoolExecutor`, controlled by a new `max_workers` setting (default: 4).

**Config** (`backend/config.py`):
- Added `max_workers: int = 4` setting for controlling thread pool size across agents

**Agent 1 — Ingest** (`backend/pipeline/agent_ingest.py`):
- File summarization now runs in parallel — each file is summarized concurrently instead of sequentially
- Extracted `_summarize_file()` as a standalone function to support parallel execution

**Agent 2 — Research** (`backend/pipeline/agent_research.py`):
- All topics are researched in parallel instead of one-by-one
- Within each topic, the two web searches (job skills + trends) also run in parallel (nested `ThreadPoolExecutor` with 2 workers)
- Extracted `_research_topic()` as a standalone function
- Result ordering is preserved using index-based slot assignment

**Agent 3 — Generate** (`backend/pipeline/agent_generate.py`):
- All learning modules are generated in parallel
- Extracted `_generate_module()` as a standalone function
- Result ordering preserved so PDF chapters match the original topic order

**Impact**: Previously ~29 minutes for a single slide file with 15 topics (all sequential API calls). Parallelization significantly reduces wall-clock time since most of the runtime is spent waiting on API responses.

---

### Domain Scoping

A new `curriculum_scope` field flows through the entire pipeline to keep all analysis and content generation strictly within the curriculum's domain. This prevents the LLM from drifting into unrelated technologies or tangential topics.

**State** (`backend/pipeline/state.py`):
- Added `curriculum_scope: str` — a one-sentence description of the curriculum's domain boundaries
- Topics now carry richer metadata: `key_techniques` (list of specific methods/algorithms) and `domain_context` (broader subject area framing)

**Pipeline runner** (`backend/run_pipeline.py`):
- `curriculum_scope` initialized as empty string in the starting state

**Ingest prompt** (`backend/prompts/ingest.py`):
- `EXTRACT_TOPICS` now asks the LLM to determine the overall curriculum scope before extracting topics
- Topics must now include `key_techniques` (3-8 specific techniques from the source material) and `domain_context`
- Added explicit instruction: "Your analysis must stay strictly within what the source material actually covers"
- Return format changed from `{"topics": [...]}` to `{"curriculum_scope": "...", "topics": [...]}`

**Research prompt** (`backend/prompts/research.py`):
- Added `SCOPE CONSTRAINT` section that explicitly forbids introducing concepts from outside the curriculum's domain
- Added `{key_techniques}` and `{curriculum_scope}` template variables
- Gap analysis now focuses on: Are the taught techniques still current? What practical skills for THESE techniques does industry expect? What alternative approaches to the SAME PROBLEM does industry prefer?
- Changed wording from generic "industry demands" to "what industry wants WITHIN this specific domain"

**Generate prompt** (`backend/prompts/generate.py`):
- Added scope instruction: "This module is part of a curriculum on '{curriculum_scope}'. All content must stay within this domain."
- All section instructions now reference `{topic_name}` specifically instead of generic phrasing
- Industry Context section explicitly says "Do NOT discuss unrelated industry trends or technologies outside the scope of {topic_name}"
- Added `{curriculum_scope}` template variable

**Agent changes**:
- `agent_ingest.py`: Now extracts `curriculum_scope` from LLM response and passes it in state
- `agent_research.py`: Passes `curriculum_scope` to gap analysis prompt; uses `key_techniques` and `domain_context` from topics for more targeted web searches
- `agent_generate.py`: Passes `curriculum_scope` to module generation prompt

---

### Improved Web Search Queries (Research Agent)

Search queries are now more targeted using the enriched topic metadata:

**Before**:
```
"{topic_name} job requirements skills 2025 2026"
"{topic_name} industry trends applications 2025 2026"
```

**After**:
```
"{technique_str} skills applications in {domain_ctx} 2025 2026"
"{topic_name} latest developments alternatives in {domain_ctx} 2025 2026"
```

Where `technique_str` is the first 4 key techniques and `domain_ctx` is the topic's domain context. This produces more relevant search results that stay within the curriculum's domain.

---

### PDF Builder Fix

**`backend/services/pdf_builder.py`**:
- The PDF title on the cover page is now passed through `_sanitize()` to prevent `UnicodeEncodeError` when the title contains smart quotes or other non-latin-1 characters

---

### Test Suite Expansion

**`backend/tests/test_pdf_builder.py`**: Expanded from 1 basic test to a comprehensive suite covering edge cases that arise from LLM-generated content.

New test categories:
- **Baseline**: Valid PDF with standard modules, correct structure and magic bytes
- **Unicode/encoding**: Smart quotes, em dashes, bullets, accented characters, CJK fallback, emoji fallback, mixed scripts
- **Malformed markdown**: Unclosed formatting, deeply nested headers, raw HTML tags, excessive blank lines
- **Edge cases**: Empty module content, very long content (20k+ chars), single topic, many topics (30+), empty topic names/descriptions
- **Markdown rendering**: Inline bold/italic, numbered lists, code blocks, blockquotes, link formatting
- **Section handling**: Missing sections, extra/unexpected sections, duplicate section headers
- **Special characters**: Backslashes, percent signs, curly braces, angle brackets, null bytes, tabs, form feeds
- **Title edge cases**: Very long titles, titles with special characters
- **Structural**: Module count mismatch (more/fewer modules than topics)

Helper utilities added:
- `_assert_valid_pdf(path, min_size)` — validates file existence, size, and PDF magic bytes
- `_build(tmp_path, topics, modules, title)` — shortcut for building test PDFs

---

### Files Changed

| File | Change |
|------|--------|
| `backend/config.py` | Added `max_workers: int = 4` |
| `backend/pipeline/state.py` | Added `curriculum_scope` field, expanded topic type annotation |
| `backend/run_pipeline.py` | Initialize `curriculum_scope` in starting state |
| `backend/pipeline/agent_ingest.py` | Parallel file summarization, extract `curriculum_scope` |
| `backend/pipeline/agent_research.py` | Parallel topic research with nested parallel web searches |
| `backend/pipeline/agent_generate.py` | Parallel module generation, pass `curriculum_scope` to prompt |
| `backend/prompts/ingest.py` | Richer topic extraction with scope, techniques, domain context |
| `backend/prompts/research.py` | Domain-scoped gap analysis with key techniques |
| `backend/prompts/generate.py` | Domain-scoped module generation |
| `backend/services/pdf_builder.py` | Sanitize title on cover page |
| `backend/tests/test_pdf_builder.py` | Expanded from 1 to 20+ rigorous tests |
