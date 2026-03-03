# Prompt Templates

All prompts live in `backend/prompts/` and use Python string `.format()` for variable interpolation.

---

## Ingest Prompts (`backend/prompts/ingest.py`)

**Model**: GPT-5-nano (temperature 0.2)

### `SUMMARIZE_FILE`

Summarizes a single curriculum file (300-500 words). Used for files <=15K chars.

**Variables**: `{source}`, `{text}`

### `SUMMARIZE_CHUNK`

Summarizes one chunk of a long file (100-200 words). Used in map-reduce for files >15K chars.

**Variables**: `{source}`, `{chunk_num}`, `{total_chunks}`, `{text}`

### `REDUCE_SUMMARIES`

Combines chunk summaries into one coherent file summary (300-500 words).

**Variables**: `{source}`, `{chunk_summaries}`

### `EXTRACT_TOPICS`

Extracts 10-25 distinct topics from combined file summaries. Returns JSON with:

```json
{
  "curriculum_scope": "...",
  "topics": [
    {
      "name": "...",
      "description": "...",
      "key_techniques": ["..."],
      "domain_context": "..."
    }
  ]
}
```

**Variables**: `{summaries}`

---

## Research Prompt (`backend/prompts/research.py`)

**Model**: GPT-5-mini (temperature 0.3)

### `GAP_ANALYSIS`

Compares curriculum coverage against industry job requirements and trends, scoped to the curriculum's domain. Returns JSON with:

```json
{
  "topic": "...",
  "severity": "critical|moderate|minor",
  "curriculum_coverage": "...",
  "industry_demands": "...",
  "gaps": ["..."],
  "enrichments": ["..."]
}
```

Severity is `critical`/`moderate`/`minor` and drives model routing in the generate agent.

**Variables**:

| Variable | Description |
|----------|-------------|
| `{topic_name}` | Name of the topic being analyzed |
| `{topic_description}` | Brief description of the topic |
| `{key_techniques}` | Techniques from curriculum |
| `{curriculum_scope}` | One-sentence domain boundary |
| `{curriculum_chunks}` | Retrieved curriculum content (ChromaDB) |
| `{job_results}` | Tavily job search results |
| `{trend_results}` | Tavily trend search results |

---

## Generate Prompt (`backend/prompts/generate.py`)

**Model**: GPT-5.1 (critical topics) / GPT-5-mini (moderate/minor topics)
**Temperature**: 0.3

### `GENERATE_MODULE`

Generates a full learning module in markdown. Content is scoped to the curriculum's domain.

**Variables**:

| Variable | Description |
|----------|-------------|
| `{topic_name}` | Name of the topic |
| `{topic_description}` | Brief description |
| `{key_techniques}` | Techniques from curriculum |
| `{curriculum_scope}` | One-sentence domain boundary |
| `{curriculum_chunks}` | Retrieved curriculum content (ChromaDB) |
| `{research_chunks}` | Industry research data (Tavily web search) |
| `{gap_analysis}` | Gap analysis JSON from research agent |

**Output Schema** -- Markdown document with exactly these sections (in order):

| Section | Content | Key Rules |
|---------|---------|-----------|
| `## Module Overview` | 3-5 sentence preview | Real-world problem/scenario, industry relevance, what student gains |
| `## Learning Objectives` | 3-5 Bloom's taxonomy objectives | Each MUST end with `(Curriculum)` or `(Gap)` tag; at least one of each |
| `## Curriculum Coverage` | What the course teaches | Draw ONLY from curriculum content; end with 2-3 quick-check questions |
| `## Identified Gaps` | What's missing | Frame as opportunities; priority tags: (Critical), (Important), (Nice-to-have) |
| `## Core Content` | Main teaching section | `### What You Need to Learn` + `### Common Misconceptions`; do NOT repeat curriculum |
| `## Industry Context` | Real-world application | 2-3 job titles, one detailed use case, employer requirements |
| `## Practice & Review` | Exercises | `### Quick Check` + `### Apply It`; mix of recall, conceptual, and application questions |
| `## Key Takeaways` | 7-10 bullet points | Prefixed: `Curriculum:`, `Gap:`, `Integration:` |
| `## Reflection` | 3 metacognitive prompts | Fixed format with self-assessment questions |
| `## Further Reading` | 3-5 curated resources | Only URLs from research data; type + difficulty tags |

**Validation**: Generated modules are checked for required sections (`## Module Overview`, `## Learning Objectives`, `## Core Content`, `## Key Takeaways`) and minimum 2,000 characters. Failed modules are retried up to 2 times.

---

## PPT Prompts (`backend/prompts/ppt.py`)

Three prompt variants for different PPT generation modes.

### `STRUCTURE_GAP_SLIDES` (Full Presentation)

**Model**: GPT-5.1 (original monolithic mode, now replaced by per-topic)
**Input variables**: `{curriculum_scope}`, `{topic_count}`, `{modules_content}`, `{gap_summary_json}`

**Output JSON schema**:

```json
{
  "presentation_title": "...",
  "executive_summary": {
    "total_gaps_found": 0,
    "topics_analyzed": 0,
    "critical_count": 0,
    "moderate_count": 0,
    "minor_count": 0,
    "critical_gaps": ["..."],
    "overall_assessment": "...",
    "topic_scores": [
      {"topic": "...", "curriculum_score": 0, "industry_requirement": 0}
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
          "diagram_data": {"nodes": ["..."], "labels": ["..."]}
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
3. 1-3 `gap_concepts` per topic; most important MUST have a diagram
4. Diagram data: 3-6 nodes with 2-5 word text each
5. NEVER use the word "gap" in any slide content -- frame as learning opportunities
6. Every topic MUST have `quiz` and `market_signal` objects
7. Topic slides follow same order as PDF chapters

### `STRUCTURE_SINGLE_TOPIC_SLIDE` (Per-Topic Mode)

**Model**: GPT-5-mini
**Purpose**: Generates one topic slide at a time (replaces monolithic call for better quality + lower per-call tokens).

**Input variables**: `{topic_name}`, `{module_content}`, `{gap_analysis_json}`, `{research_chunks}`

**Output**: Same schema as a single `topic_slides` entry above.

**Additional rule**: `market_signal.stat` MUST be a real number extracted from `{research_chunks}` -- no invented statistics.

### `STRUCTURE_EXECUTIVE_SUMMARY` (Overview Slide)

**Model**: GPT-5-nano
**Purpose**: Generates only the executive summary data (stats, scores, assessment) for the overview slides.

**Input variables**: `{curriculum_scope}`, `{topics_analyzed}`, `{total_gaps_found}`, `{critical_count}`, `{moderate_count}`, `{minor_count}`, `{topic_severities_json}`, `{critical_gaps_sample}`

**Output**: The `executive_summary` portion of the full schema.

---

## Video Prompts (`backend/prompts/video.py`)

### `HOOK_EXAMPLES`

Reference list of hook types used to enforce variety across scripts:

| # | Hook Type | Example Opening |
|---|-----------|-----------------|
| 1 | Curiosity Question | "What if I told you..." |
| 2 | Scenario | "Imagine you're on your first day as a [role]..." |
| 3 | Statistic | "80% of job postings require Y..." |
| 4 | Misconception | "Most students think X works like Y..." |
| 5 | Value Promise | "In the next 3 minutes, you'll learn..." |

Hook variety is enforced via thread-safe tracking across scripts.

### `MODULE_TO_SCRIPT` (Standalone Module Script)

**Model**: GPT-5.1 (temperature 0.55)
**Purpose**: Generates a video script from a single learning module (fallback when PPT is not selected).

**Input variables**: `{topic_name}`, `{module_content}`, `{curriculum_chunks}`, `{research_chunks}`, `{hook_guidance}`

**6-Section Structure** (continuous spoken text, no labels):

| Section | Word Count | Duration | Content |
|---------|-----------|----------|---------|
| Hook | 30-45 | 10-15s | Topic-specific hook |
| Anchor | 45-60 | 15-20s | Connect to prior knowledge |
| Teach the Gap | 300-450 | 2-3 min | Core teaching (definitions, examples, step-by-step) |
| Misconception | 60-90 | 20-30s | "A lot of students think... But here's the thing..." |
| Retrieval Prompt | 30-45 | 10-15s | Pause and think prompt |
| Takeaways | 60-90 | 20-30s | 3-4 key points + forward-looking close |

**Target**: 300-750 words, under 4,500 characters.

### `SCRIPT_FROM_SLIDES` (PPT-Synced Script)

**Model**: GPT-5.1 (temperature 0.55)
**Purpose**: Generates a video script synced to a specific PPT topic slide. This is the primary mode when PPT is selected.

**Input variables**: `{topic_name}`, `{severity}`, `{topic_slide_json}`, `{curriculum_chunks}`, `{research_chunks}`, `{modules_content}`, `{research_context}`, `{curriculum_anchor}`, `{misconception_wrong}`, `{misconception_right}`, `{hook_guidance}`

**6-Section Structure** (same sections, tighter word counts):

| Section | Word Count | Duration | Additional Rules |
|---------|-----------|----------|-----------------|
| Hook | 25-35 | -- | Severity-aware urgency |
| Anchor | 40-55 | -- | Uses `curriculum_anchor` directly |
| Teach the Gap | 200-320 | -- | Follow `gap_concepts` IN ORDER from PPT slide; reference diagrams |
| Misconception | 50-70 | -- | Rephrase, don't read verbatim |
| Retrieval Prompt | 25-35 | -- | -- |
| Takeaways | 50-75 | -- | -- |

**Target**: 400-600 words (aim ~500), under 3,800 characters.

---

## Voice and Framing Rules

These rules apply across ALL prompts and builders:

1. **"You" voice**: Address the student directly ("You already know...", "Here's how industry applies this...")
2. **No gap language**: NEVER use "gap analysis", "what's missing", "coverage falls short" in student-facing content. JSON field names like `gap_concepts` are internal only.
3. **Positive framing**: Frame industry differences as "here's what you'll learn next" or "industry takes this further by..."
4. **Assertion-evidence titles**: Slide titles must be full teaching assertions, not short labels. "Skip-gram requires sampled objectives to scale to real-world vocabularies." NOT "Skip-gram Issues"
5. **Curriculum grounding**: All claims must be supported by curriculum content or industry research -- no hallucination
6. **Mandatory contractions** (video scripts): "you'll" not "you will", "it's" not "it is"
7. **Severity-to-priority mapping**: `critical` = Essential, `moderate` = Recommended, `minor` = Supplementary

### Key Rules for Both Script Prompts

1. Write ONLY spoken words -- no stage directions, markdown, headers, asterisks
2. Conversational "you" language throughout
3. **Contractions are MANDATORY**: "you'll" not "you will", "it's" not "it is", etc.
4. Do NOT duplicate slide content verbatim -- complement it
5. No URLs, citations, or "further reading" references
6. Single continuous text block with paragraph breaks for natural pauses
