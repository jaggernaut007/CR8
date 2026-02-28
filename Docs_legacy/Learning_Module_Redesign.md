> **DEPRECATED** — This file has been superseded by the new documentation site at `docs/`. See `docs/design/learning-module-redesign.md` for the current version.
>
> This file is kept for reference only and will be removed in a future cleanup.

---

# Learning Module Redesign: Evidence-Based Implementation Guide

## Why This Redesign

The CR8 pipeline collects three rich data sources — curriculum content, industry research, and gap analysis — but the current module generation prompt underutilizes them. The Core Content section, which should be the main teaching body, receives a single sentence of guidance: *"Clear explanation of the topic drawn from curriculum materials."* It rehashes what the student already learned and ignores the gap and research data entirely.

This redesign restructures the learning module based on peer-reviewed pedagogical research to produce guides that **actually teach the student what they're missing**, not just tell them they're missing it.

---

## The Problem with the Current Design

### Current module structure (7 sections)

```
1. Curriculum Coverage    ← Summarizes what the student already learned
2. Identified Gaps        ← Tells them what's missing
3. Learning Objectives    ← States what they should learn
4. Core Content           ← "Clear explanation drawn from curriculum materials" (1 line of guidance)
5. Industry Context       ← Where skills are used
6. Key Takeaways          ← Summary bullets
7. Further Reading        ← Links
```

### What's wrong

| Issue | Impact |
|-------|--------|
| **Core Content only draws from curriculum** | The student reads a summary of what they already learned. The research and gap data the system collected goes unused in the teaching section. |
| **Core Content has 1 line of prompt guidance** | Every other section has detailed, multi-bullet instructions. The actual teaching body is the least specified section. |
| **Three diagnostic sections before any teaching** | The student reads analysis about what they know and don't know before encountering any new learning. This violates Gagne's Nine Events of Instruction. |
| **No active learning components** | Zero exercises, practice questions, or retrieval practice. The entire module is passive reading. |
| **No formative assessment** | Learning objectives are stated but never assessed. The student can't verify they met them. |
| **Gaps are diagnosed but never taught** | The system identifies what the curriculum misses, then never actually teaches those concepts. |

---

## New Module Structure (10 sections)

```
 1. Module Overview         ← Hook + real-world problem
 2. Learning Objectives     ← What you'll be able to do (moved up)
 3. Curriculum Coverage     ← What you already know + self-check
 4. Identified Gaps         ← What's missing, prioritized
 5. Core Content            ← TEACHES the gaps (entirely gap-focused)
 6. Industry Context        ← Where and how these skills are used
 7. Practice & Review       ← Retrieval practice + hands-on scenario
 8. Key Takeaways           ← Summary with Curriculum/Gap/Integration tags
 9. Reflection              ← Metacognitive prompts
10. Further Reading         ← Categorized resources with difficulty levels
```

---

## Section-by-Section Design with Research Rationale

### 1. Module Overview (NEW)

**What it does:** Opens with a real-world problem or scenario that the topic's knowledge solves, previews what the module covers, and hooks the student into reading further.

**Research basis:**

- **Merrill's First Principles of Instruction** — Learning is promoted when learners engage with real-world problems. The problem-centered approach has been validated across multiple meta-analyses as significantly improving transfer and retention compared to topic-centered instruction.
  - Source: Merrill, M.D. (2002). "First Principles of Instruction." *Educational Technology Research & Development*, 50(3), 43-59.

- **Advance Organizers (Ausubel)** — Presenting a high-level conceptual framework before detailed content significantly improves learning and retention. Advance organizers work by activating relevant prior knowledge and providing a structure for incoming information.
  - Source: Ausubel, D.P. (1960). "The use of advance organizers in the learning and retention of meaningful verbal material." *Journal of Educational Psychology*, 51(5), 267-272.

- **Gagne's Event #1: Gain Attention** — Instruction should begin by gaining the learner's attention through a stimulus change, question, or problem statement.
  - Source: Gagne, R.M. (1985). *The Conditions of Learning and Theory of Instruction*. Holt, Rinehart & Winston.

**Prompt instruction:**
> 3-5 sentences: what this module covers, why it matters right now, and a brief real-world scenario or problem that this topic's knowledge solves. Draw from all sources to frame relevance. End with a question or hook that motivates reading further.

---

### 2. Learning Objectives (MOVED from position #3 to #2)

**What it does:** States 3-5 specific, measurable learning objectives using Bloom's taxonomy verbs, tagged as (Curriculum) or (Gap).

**Research basis:**

- **Constructive Alignment (Biggs)** — Learning outcomes, teaching activities, and assessment must all point at the same target. Placing objectives before content ensures the student knows what they're working toward.
  - Source: Biggs, J. (1996). "Enhancing teaching through constructive alignment." *Higher Education*, 32(3), 347-364.

- **Gagne's Event #2: Inform Learner of Objectives** — Telling learners what they will be able to do after instruction sets appropriate expectations and focuses attention on relevant content.

- **Bloom's Revised Taxonomy** — Using verbs from specific cognitive levels (Remember, Understand, Apply, Analyze, Evaluate, Create) ensures objectives are measurable and appropriately challenging.
  - Source: Anderson, L.W. & Krathwohl, D.R. (2001). *A Taxonomy for Learning, Teaching, and Assessing*. Longman.

**Why moved up:** In the current design, objectives appear after Curriculum Coverage and Identified Gaps (position #3). Research on instructional sequencing shows that learners benefit from knowing objectives before engaging with content, not after reading two analytical sections.

**Prompt instruction (enhancement):**
> Same as current, plus: "Include at least one objective at the Apply level or higher. Gap-tagged objectives should target higher Bloom's levels (Apply, Analyze, Evaluate) because they address skills the student needs to build, not just recall."

---

### 3. Curriculum Coverage (KEPT, minor enhancement)

**What it does:** Summarizes what the original course materials teach about the topic, drawing only from curriculum content.

**Research basis:**

- **Gagne's Event #3: Stimulate Recall of Prior Learning** — Connecting new material to what learners already know activates relevant schemas and prepares them for new information.

- **Merrill's Activation Principle** — Learning is promoted when learners activate existing knowledge as a foundation for new knowledge.

**What's new:** Added quick-check retrieval questions at the end. This is based on:

- **Retrieval Practice (Dunlosky et al., 2013)** — Rated as the highest-utility learning technique across hundreds of studies. Testing oneself on material (even without feedback) produces stronger long-term retention than re-reading.
  - Source: Dunlosky, J. et al. (2013). "Improving Students' Learning With Effective Learning Techniques." *Psychological Science in the Public Interest*, 14(1), 4-58.

**Prompt instruction (enhancement):**
> Same as current, plus: "End with 2-3 quick-check questions: 'Before continuing, make sure you can answer: ...'. These should test recall of the key curriculum concepts."

---

### 4. Identified Gaps (KEPT, reframed)

**What it does:** Describes gaps between curriculum and industry demands, prioritized by importance.

**Research basis:**

- **Growth Mindset Framing (Dweck)** — Research shows that framing challenges as opportunities for growth (rather than deficiencies) improves motivation and persistence. The prompt now instructs the LLM to frame gaps as opportunities.
  - Source: Dweck, C.S. (2006). *Mindset: The New Psychology of Success*. Random House.

- **Expectancy-Value Theory** — Students are more motivated when they understand the value of what they're learning. Prioritizing gaps by industry frequency helps students allocate effort effectively.
  - Source: Wigfield, A. & Eccles, J.S. (2000). "Expectancy-Value Theory of Achievement Motivation." *Contemporary Educational Psychology*, 25(1), 68-81.

**What's new:** Gap prioritization (Critical / Important / Nice-to-have) and growth-oriented language.

**Prompt instruction (enhancement):**
> Same as current, plus: "Frame each gap as an opportunity to build valuable skills, not a deficiency. For each gap, indicate priority (Critical / Important / Nice-to-have) based on how frequently it appears in industry demands."

---

### 5. Core Content (MAJOR OVERHAUL — entirely gap-focused)

**What changed:** The entire Core Content section is now focused on **teaching the gap concepts**, not rehashing curriculum. Curriculum Coverage already handles the recap. This section exists to close the knowledge gaps the system identified.

**Structure:**

```
### What You Need to Learn
[Deep teaching of top 1-2 critical gaps]
[Brief summaries of remaining gaps with pointers to Further Reading]

### Common Misconceptions
[2-3 misconceptions about the gap concepts]
```

**Research basis:**

- **Merrill's Demonstration Principle** — Learning is promoted when the instruction demonstrates what is to be learned. The current "clear explanation" instruction is too vague. Worked examples with step-by-step reasoning are the most effective form of demonstration.
  - Source: Merrill, M.D. (2002). "First Principles of Instruction."

- **Worked Example Effect (Sweller, Cognitive Load Theory)** — Worked examples significantly reduce cognitive load for novices and improve knowledge retention. Studying a fully worked example is more effective than solving an equivalent problem for learners who are new to a concept.
  - Source: Sweller, J. (1988). "Cognitive Load During Problem Solving: Effects on Learning." *Cognitive Science*, 12(2), 257-285.
  - Confirmed by: Atkinson, R.K. et al. (2000). "Learning from Examples: Instructional Principles from the Worked Examples Research." *Review of Educational Research*, 70(2), 181-214.

- **Scaffolding from Known to Unknown (Vygotsky)** — New concepts should be anchored to existing knowledge. Each gap concept begins with "Building on [curriculum concept]..." to create a bridge from familiar to unfamiliar.
  - Source: Vygotsky, L.S. (1978). *Mind in Society: The Development of Higher Psychological Processes*. Harvard University Press.

- **Depth over Breadth for Critical Concepts** — Research on learning transfer shows that deep understanding of fewer concepts produces better outcomes than shallow coverage of many. The top 1-2 gaps are taught fully; lesser gaps get summaries.
  - Source: Bransford, J.D. et al. (2000). *How People Learn: Brain, Mind, Experience, and School*. National Academy Press.

- **Misconception-Targeted Instruction** — Research shows that directly addressing common misconceptions is more effective than simply presenting correct information, because learners often assimilate new information into existing incorrect mental models.
  - Source: Chi, M.T.H. (2005). "Commonsense Conceptions of Emergent Processes." *Journal of the Learning Sciences*, 14(2), 161-199.

**Why gap-focused only:**
The Curriculum Coverage section (position #3) already summarizes what the student learned in class. Teaching it again in Core Content would be redundant and waste the student's time. The entire value proposition of the CR8 system is enriching curriculum with industry-relevant knowledge — so the main teaching section should teach what's missing, not what's already covered.

**Prompt instruction:**

> **### What You Need to Learn**
> Identify the top 1-2 most critical gaps from the GAP ANALYSIS (the ones most frequently demanded by industry). For each gap, TEACH the concept fully:
> - Anchor it to something the student already learned ("Building on [curriculum concept]...")
> - Define the concept clearly with a precise definition
> - Explain how it works with a detailed walkthrough or worked example
> - Walk through application step by step (use numbered steps: 1., 2., 3.)
> - Include a concrete example from current industry practice
> The student should be able to understand and apply these concepts from this section alone, without needing external resources. Write 3-5 paragraphs per gap concept.
>
> For any remaining lesser gaps, provide a brief summary (1-2 sentences each): what it is, why it matters, and where to learn more (reference the Further Reading section).
>
> Draw from INDUSTRY RESEARCH and GAP ANALYSIS. Do NOT rehash curriculum content — assume the student already knows it.
>
> **### Common Misconceptions**
> List 2-3 things students commonly get wrong about {topic_name}, focusing on misconceptions related to the gap concepts taught above:
> - State the misconception
> - Explain why it's wrong
> - Provide the correct understanding

---

### 6. Industry Context (KEPT, enhanced)

**What it does:** Shows how the topic applies in real industry roles with specific job titles and use cases.

**Research basis:**

- **Gagne's Event #9: Enhance Retention and Transfer** — Instruction should help learners transfer knowledge to new contexts. Specific industry examples provide concrete mental models for transfer.

- **Relevance Framing (Self-Determination Theory)** — Research published in Frontiers in Psychology (2023) demonstrates that increasing content relevance has a strong effect on autonomous motivation, effort, and vitality. Connecting learning to near-term career goals is more effective than abstract future rationales.
  - Source: Patall, E.A. et al. (2023). "Relevance and autonomous motivation." *Frontiers in Psychology*, 14.

**Prompt instruction (enhancement):**
> Same as current, plus: "Include 2-3 specific job titles where this skill is valued, and describe one real-world use case in detail."

---

### 7. Practice & Review (NEW)

**What it does:** Provides retrieval practice questions and a realistic hands-on scenario that combines curriculum and gap knowledge.

**Research basis:**

- **Retrieval Practice — the single highest-impact technique.** Dunlosky et al. (2013) rated practice testing as "high utility" — the strongest rating — based on extensive evidence. A 2024 state-of-the-art review in health professions education confirmed that most studies and meta-analyses demonstrate positive benefits, with effects extending to clinical and practical applications.
  - Source: Dunlosky et al. (2013). *Psychological Science in the Public Interest*, 14(1), 4-58.
  - Source: State-of-the-art review, PMC (2024). DOI: 10.1007/s40037-024-00905-7

- **Mixed-Format Questions** — A 2024 comparative study found that both very short answer questions (VSAQs) and multiple-choice questions (MCQs) are effective for retrieval practice. VSAQs provide more reliable insight into genuine understanding, while MCQs are faster to complete.
  - Source: PMC (2024). DOI: 10.1186/s12909-024-06427-4

- **Application Exercises (Merrill's Application Principle)** — Learning is promoted when learners apply new knowledge to solve problems. The "Apply It" scenario requires integration of both curriculum and gap knowledge, forcing deeper processing.

- **Elaborative Interrogation** — Generating explanations for why facts are true promotes deep processing by forcing integration of new information with prior knowledge. Rated "moderate utility" by Dunlosky et al.

**Prompt instruction:**

> **### Quick Check**
> 3-5 retrieval practice questions mixing formats:
> - 2 factual recall questions (from Curriculum Coverage)
> - 1 conceptual question (from Core Content gap concepts)
> - 1 application question connecting curriculum knowledge to a gap concept
> Provide brief answers after each question.
>
> **### Apply It**
> One realistic scenario (4-6 sentences) requiring the student to use both curriculum and gap-bridging knowledge. List 3-4 specific tasks within the scenario. Describe the expected outcome.

---

### 8. Key Takeaways (KEPT — no changes)

**What it does:** 7-10 bullet points structured as Curriculum / Gap / Integration.

**Research basis:** The three-tier structure is already well-designed. The Integration bullets force synthesis across knowledge domains, which is a form of elaborative interrogation. No changes needed.

---

### 9. Reflection (NEW)

**What it does:** Three metacognitive prompts that ask the student to reflect on their learning.

**Research basis:**

- **Metacognitive Prompts** — A meta-analysis by Guo (2022) found that metacognitive prompts significantly enhanced self-regulated learning activities and learning outcomes relative to control conditions. Students who reflected on their learning showed better retention and transfer.
  - Source: Guo, L. (2022). "Effects of metacognitive prompts on self-regulation and learning." *Journal of Computer Assisted Learning*, 38(6).

- **Confidence-Based Self-Assessment** — Research on calibration (Dunlosky & Rawson, 2012) shows that asking students to rate their confidence helps identify areas of false confidence (illusion of knowledge) and directs further study.
  - Source: Dunlosky, J. & Rawson, K.A. (2012). "Overconfidence produces underachievement." *Learning and Instruction*, 22(4), 271-280.

**Prompt instruction:**

> 3 metacognitive prompts:
> - "What was the most important thing you learned in this module?"
> - "Which gap area do you feel least confident about? What would help you strengthen it?"
> - "How does {topic_name} connect to other topics you've studied?"

---

### 10. Further Reading (KEPT, enhanced)

**What it does:** 3-5 curated resources from the research data, now categorized by type and difficulty.

**Research basis:**

- **Scaffolded Resource Selection** — Research on self-regulated learning shows that students make better study choices when resources are annotated with difficulty levels and types, rather than presented as undifferentiated lists.
  - Source: Winne, P.H. & Hadwin, A.F. (1998). "Studying as self-regulated learning." In *Metacognition in Educational Theory and Practice* (pp. 277-304). Erlbaum.

**Prompt instruction (enhancement):**
> Same as current, plus: "Categorize each resource as (Tutorial / Documentation / Research Paper / Video). Indicate difficulty (Beginner / Intermediate / Advanced). Order as a suggested learning sequence."

---

## PDF Renderer Enhancements

The current PDF renderer only handles `## ` headings, `- ` bullet points, and plain paragraphs. The redesigned module requires three additional elements:

| Element | Pattern | Styling | Rationale |
|---------|---------|---------|-----------|
| `### ` sub-headings | `stripped.startswith("### ")` | Teal bold Helvetica 11pt, no underline | Core Content and Practice & Review use sub-sections |
| Numbered lists | `re.match(r"^\d+\.\s", stripped)` | Teal number + charcoal text | Worked examples use numbered steps |
| Blockquotes | `stripped.startswith("> ")` | Gold left bar, slate gray italic 9pt | Practice answers and callouts |

These additions support the pedagogical goal of varied content presentation (Universal Design for Learning — multiple means of representation).

---

## Learning Journey Summary

After completing one redesigned module, the student will have:

1. **Been hooked** by a real-world problem that makes the topic relevant (Module Overview)
2. **Known exactly** what they'll be able to do (Learning Objectives)
3. **Refreshed** what they already know and self-checked their recall (Curriculum Coverage)
4. **Understood** what they're missing and why it matters, prioritized by industry importance (Identified Gaps)
5. **Actually learned** the top 1-2 critical gap concepts through full definitions, worked examples, and step-by-step walkthroughs — deeply enough to apply them without external resources (Core Content)
6. **Seen** where and how these skills are used in real industry roles (Industry Context)
7. **Tested themselves** with retrieval practice and applied knowledge to a realistic scenario (Practice & Review)
8. **Consolidated** understanding through structured takeaways (Key Takeaways)
9. **Reflected** on their learning and identified remaining weak areas (Reflection)
10. **Received** a curated, categorized path for continued learning (Further Reading)

---

## Research References

| Research Area | Key Source | Finding | How We Use It |
|---------------|-----------|---------|---------------|
| Instructional sequencing | Gagne (1985). *Conditions of Learning* | Nine Events of Instruction provide optimal ordering | New section order follows Gagne's events |
| Problem-first learning | Merrill (2002). "First Principles of Instruction" | Real-world problems improve transfer | Module Overview opens with scenario |
| Advance organizers | Ausubel (1960). *J. Educational Psychology* | Previewing structure improves comprehension | Module Overview serves as organizer |
| Constructive alignment | Biggs (1996). *Higher Education* | Objectives, content, assessment must align | Objectives moved before content |
| Retrieval practice | Dunlosky et al. (2013). *Psych. Sci. in Public Interest* | Highest-utility learning technique | Practice & Review section added |
| Worked examples | Sweller (1988). *Cognitive Science* | Reduce cognitive load for novices | Core Content teaches gaps with walkthroughs |
| Scaffolding | Vygotsky (1978). *Mind in Society* | Bridge known to unknown | Gap concepts anchored to curriculum knowledge |
| Depth over breadth | Bransford et al. (2000). *How People Learn* | Deep understanding > shallow coverage | Top 1-2 gaps taught fully, rest summarized |
| Misconception targeting | Chi (2005). *J. Learning Sciences* | Directly address incorrect mental models | Common Misconceptions sub-section |
| Growth mindset framing | Dweck (2006). *Mindset* | Opportunity framing > deficit framing | Gaps reframed as growth opportunities |
| Metacognitive prompts | Guo (2022). *J. Computer Assisted Learning* | Reflection enhances self-regulated learning | Reflection section added |
| Relevance framing | Patall et al. (2023). *Frontiers in Psychology* | Relevance drives autonomous motivation | Industry Context enhanced with specifics |
| Cognitive load theory | Sweller (1988). *Cognitive Science* | Minimize extraneous load, maximize germane | Sub-headings, chunking, consistent formatting |
| Spaced retrieval | Dunlosky et al. (2013) | Distributed practice rated "high utility" | Further Reading suggests review schedule |
| Content relevance | Wigfield & Eccles (2000). *Contemporary Ed. Psych.* | Value perception drives effort | Gap prioritization by industry frequency |

---

## Implementation Files

### Phase 1: PDF Learning Module Redesign

| File | Change |
|------|--------|
| `backend/prompts/generate.py` | Complete rewrite of GENERATE_MODULE prompt (7 sections to 10 sections) |
| `backend/services/pdf_builder.py` | Add `###` sub-headings, numbered lists, blockquote rendering |
| `backend/tests/test_pdf_builder.py` | Update fixtures, add tests for new rendering elements |

### Phase 2: PPT Teaching-First Overhaul

| File | Change |
|------|--------|
| `backend/prompts/ppt.py` | Teaching-first prompts with quiz, market_signal, and `{research_chunks}` input field. No "gap" language in content. "You" voice throughout. |
| `backend/services/ppt_builder.py` | 8 slide type builders: title, overview, radar chart, scorecard, topic teaching (assertion-evidence + 3 diagram types), market intelligence spotlight (split layout), quiz/reflection (A-D options), recommendations (process flow), closing. Tree layout for concept maps. Text overflow prevention. |
| `backend/pipeline/agent_generate.py` | `_structure_single_topic_slide()` receives ChromaDB research chunks. `_structure_slides_parallel()` passes `chroma_cache`. `_build_fallback_slide_data()` includes stub quiz + market_signal. |
| `backend/evals/structural/ppt_checks.py` | Accepts both `gap_concepts`/`concepts` and `severity`/`importance` field names for backwards compatibility |
| `pyproject.toml` | Add `matplotlib>=3.8` dependency |

### Phase 3: Video Script Overhaul

| File | Change |
|------|--------|
| `backend/prompts/video.py` | Complete rewrite of both prompts + `HOOK_EXAMPLES` constant; 6-section spoken structure |
| `backend/pipeline/agent_generate.py` | Per-topic PPT-aligned script generation with ChromaDB retrieval; replaces single-script flow |
| `backend/services/video_builder.py` | Synthesia scaffold stubs, configurable emotion/speed, `_slide` suffix naming, provider dispatch |
| `backend/config.py` | Add Synthesia config fields, `video_provider`, `video_avatar_emotion`, `video_avatar_speed`; increase `video_topic_limit` to 5 |
| `backend/run_pipeline.py` | Provider-aware validation (HeyGen vs Synthesia) |

---

## PPT Overhaul: Teaching-First Visual Slides

### Design Evolution

The PPT has gone through three design phases:

| Phase | Design | Issue |
|-------|--------|-------|
| **V1 (Original)** | Split-panel diagnostic layout (curriculum vs industry) | Read like an audit report, not a learning resource |
| **V2 (Gap-Focused)** | Assertion-evidence teaching slides with diagrams | Still used "gap analysis" framing and labels — felt like a diagnostic |
| **V3 (Current)** | Teaching-first with market intelligence + quiz slides | Seamless add-on to curriculum — no "gap" language, addresses student directly |

**V3 key principles:**
- **No "gap" language anywhere** — all content frames industry concepts as learning opportunities, never as deficiencies
- **"You" voice throughout** — addresses the student directly ("You already know...", "Here's how industry applies this...")
- **Teaching, not analysis** — the PPT should feel like a natural continuation of the course
- **Industry relevance preserved** — the difference between curriculum and industry IS the product's value, just framed as "here's what to learn next"

### Current PPT Slide Architecture

```
 1. Title Slide (Dark)                 [Course title, no "gap analysis" subtitle]
 2. Course Overview                    [5 stat cards: Essential/Recommended/Supplementary]
 3. Coverage Radar Chart               [matplotlib: "Your Course" vs "Industry Standard"]
 4. Topics at a Glance                 [Scorecard with priority badges]
 5. Section Divider                    ["Topics & Concepts"]
 6–N. Per-topic slide groups (×3 slides each):
     a. Topic Teaching Slide           [Assertion-evidence with diagrams + misconceptions]
     b. Market Intelligence Spotlight  [NEW — split layout: signal + "What This Means For You"]
     c. Quiz / Reflection              [NEW — retrieval practice with A-D options]
 N+1. Section Divider                  ["What to Learn Next"]
 N+2. Recommendations                  [Process flow + prioritised actions]
 N+3. Closing (Key Takeaways)          [Numbered points on dark navy]
```

### Slide-by-Slide Design with Research Rationale

#### 1. Title Slide

Clean dark navy slide with course title centred. No "gap analysis" subtitle — just the course name and CR8 branding. Sets the tone as a teaching resource, not a diagnostic.

#### 2. Course Overview

5 stat cards showing: total concepts covered, topics, and breakdown by priority (Essential / Recommended / Supplementary). Uses teal/gold/slate colour coding instead of red/amber/green to avoid alarming framing.

**Research basis:**
- **Mayer's Signaling Principle** — The priority breakdown immediately signals where attention should be focused.

#### 3. Coverage Radar Chart

Matplotlib-generated radar chart: teal polygon for "Your Course", gold polygon for "Industry Standard". The visual space between them highlights where the supplement adds value.

**Research basis:**
- **Spatial Contiguity (Mayer)** — Integrates all topic comparisons into one visual
- **Pre-attentive Processing (Cleveland & McGill, 1984)** — Area differences perceived at a glance
- **Dual Coding (Paivio, 1986)** — Verbal stats + visual chart = two encoding channels

**Implementation:** matplotlib, transparent background, 150 DPI, embedded as PNG.

#### 4. Topics at a Glance

Scorecard table with alternating teal-tinted rows. Each topic shows name, priority badge (ESSENTIAL/RECOMMENDED/SUPPLEMENTARY), and concept count.

#### 5a. Topic Teaching Slide (per topic)

Full-width assertion-evidence layout that TEACHES each topic's concepts with diagrams.

```
+--------------------------------------+
| Assertion Title (full sentence)  [BADGE]|
| Teal accent line                        |
| You already know: [1-sentence anchor]   |
|                                         |
| [Concept 1]          | [Concept 2]     |
|  Definition           |  Definition     |
|  Why it matters box   |  Why it matters |
|  [DIAGRAM]            |  [DIAGRAM]      |
|  How it works         |  How it works   |
|                                         |
| [COMMON ASSUMPTION]  [WHAT'S ACTUALLY TRUE] |
+-----------------------------------------+
```

**Key design decisions:**
- Assertion titles state the key claim (Garner & Alley, 2013 — 15-20% better recall)
- 1-sentence curriculum anchor using "You already know..." (Mayer's Coherence — exclude extraneous material)
- Each concept is a self-contained card (Mayer's Segmenting — learner-paced segments)
- Misconception callouts use refutational text pattern (Tippett, 2010)
- Labels reframed: "COMMON ASSUMPTION" / "WHAT'S ACTUALLY TRUE" (not "WRONG" / "RIGHT")
- Text overflow prevention: right-edge padding, 250-char truncation on how_it_works

#### 5b. Market Intelligence Spotlight (NEW — per topic)

**Design spec:** Layout 6 from CR8_Course_PPT_Template_Recommendation.md. This layout is unique to CR8 — no off-the-shelf template has it.

```
+------------------+------------------+
| DARK NAVY        | OFF-WHITE        |
| [MARKET SIGNAL]  | WHAT THIS MEANS  |
| Topic name       |   FOR YOU        |
|                  | ──────           |
| Key finding      | Context text     |
| (large white)    | (14pt charcoal)  |
|                  |                  |
|     92%          | KEY EVIDENCE     |
| (big gold stat)  | • point 1        |
| stat label       | • point 2        |
|                  | • point 3        |
|                  |                  |
|                  | Source: ...       |
+------------------+------------------+
```

**Research basis:**
- **Relevance Framing (Self-Determination Theory)** — Connecting learning to career goals drives autonomous motivation (Patall et al., 2023)
- **Dual Coding (Paivio)** — Big stat number = visual encoding; context text = verbal encoding
- **Mayer's Signaling Principle** — The gold stat number and "MARKET SIGNAL" badge direct attention

**Data grounding:** The market signal data flows from real Tavily web search results → ChromaDB research collection → `{research_chunks}` in the PPT prompt. The prompt's rule 9 requires the LLM to extract real statistics from the research data, not invent them.

#### 5c. Quiz / Reflection Slide (NEW — per topic)

**Design spec:** Layout 7 from CR8_Course_PPT_Template_Recommendation.md.

```
+--------------------------------------+
| [TEAL HEADER BAR]                    |
| CHECK YOUR UNDERSTANDING — Topic     |
| Test what you've learned             |
+--------------------------------------+
|                                      |
| Question text (Georgia 22pt)         |
|                                      |
|  (A)  Option text                    |
|  (B)  Option text                    |
|  (C)  Option text                    |
|  (D)  Option text                    |
|                                      |
| +----------------------------------+ |
| | Reflection prompt (gold italic)  | |
| +----------------------------------+ |
+--------------------------------------+
```

**Research basis:**
- **Retrieval Practice (Dunlosky et al., 2013)** — Rated "high utility" — the single highest-impact learning technique. Testing oneself produces stronger long-term retention than re-reading.
- **Mixed-Format Questions (PMC, 2024)** — MCQs are effective for retrieval practice and faster to complete
- **Metacognitive Prompts (Guo, 2022)** — The reflection prompt ("Think about how...") enhances self-regulated learning and helps identify areas of false confidence

**Design details:**
- Teal lettered circles (A, B, C, D) for answer options
- Question tests the most important concept from the topic's teaching slide
- Gold-tinted reflection prompt connects the topic to the student's career
- The quiz is answerable from the teaching slide content alone

#### Topic Teaching Slide: Curriculum Anchor

The anchor uses "You already know..." voice — one sentence only. The student has already reviewed curriculum knowledge in the PDF (section 3). The PPT's job is to teach what's new, not repeat what's known.

#### Diagram Types

Three diagram helpers render gap concepts visually using native python-pptx shapes:

**Process Flow** (`_add_process_flow_diagram`):
- Rounded rectangles connected left-to-right by arrow shapes
- Use for: workflows, pipelines, deployment steps, sequential processes
- Adaptive spacing based on node count, capped node height at 0.7"

**Comparison** (`_add_comparison_diagram`):
- Two columns with headers (slate/teal), adaptive row spacing
- Use for: curriculum approach vs industry approach, before/after, theory vs practice
- Items capped at 4 per column to prevent overflow

**Concept Map** (`_add_concept_map_diagram`):
- Tree/mind-map layout with trunk + vertical spine + horizontal branches
- Central concept on left → trunk line → vertical spine → branch lines → satellite nodes
- Use for: showing relationships between concepts, taxonomies, dependencies
- Max 5 satellites, vertically centred within available space

```
[Center] ──── ┬── [Satellite 1]
              ├── [Satellite 2]
              └── [Satellite 3]
```

**Research basis for diagrams:**
- **Mayer's Multimedia Principle** — Words + pictures > words alone
- **Cognitive Load Theory (Sweller)** — Diagrams externalize relationships, freeing working memory
- **Spatial Ability (Hegarty & Waller, 2005)** — Visual representations benefit learners with lower spatial ability

**LLM diagram specification:** The prompt specifies `diagram_type` and `diagram_data` per concept. The builder renders the visual. LLM focuses on content; code handles layout.

#### Recommendations Slide

Process flow at top: "Review Concepts" → "Plan Your Study" → "Practice Skills" → "Apply in Projects" (colour-coded by stage). Below: prioritised action items with coloured stripe indicators.

**Research basis:**
- **Goal-Setting Theory (Locke & Latham, 2002)** — Concrete process increases follow-through vs abstract advice

### JSON Data Structure

The LLM prompt produces a teaching-focused JSON structure. Field names like `gap_concepts` and `severity` are kept as internal identifiers for pipeline compatibility — the actual CONTENT never uses the word "gap".

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
    "overall_assessment": "2-3 sentences, 'you' voice",
    "topic_scores": [
      {"topic": "...", "curriculum_score": 0-100, "industry_requirement": 0-100}
    ]
  },
  "topic_slides": [
    {
      "topic_name": "...",
      "slide_title": "Full assertion sentence (max 12 words)",
      "severity": "critical|moderate|minor",
      "curriculum_anchor": "You already know... (1 sentence)",
      "gap_concepts": [
        {
          "concept_name": "short name (3-5 words)",
          "definition": "1-2 sentence clear definition",
          "why_it_matters": "1 sentence — 'Industry uses...' or 'In production...'",
          "how_it_works": "2-3 sentence explanation with example, 'you' voice",
          "impact": "high|medium|low",
          "diagram_type": "process_flow|comparison|concept_map|none",
          "diagram_data": {"nodes": [...], "labels": [...]}
        }
      ],
      "misconception": {
        "wrong": "You might think... (1 sentence)",
        "right": "Actually, ... (1 sentence)"
      },
      "quiz": {
        "question": "Retrieval-practice question (1-2 sentences)",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "correct": "B",
        "reflection_prompt": "Career-focused thought prompt (1 sentence)"
      },
      "market_signal": {
        "signal": "Key industry finding (1-2 sentences)",
        "stat": "85%",
        "stat_label": "descriptor of what the stat measures",
        "context": "2-3 sentences, 'you' voice",
        "supporting_points": ["evidence 1", "evidence 2", "evidence 3"],
        "source": "Actual research source name"
      },
      "top_recommendations": ["..."]
    }
  ],
  "recommendations_summary": [
    {"priority": "high|medium|low", "action": "...", "topics_affected": ["..."]}
  ]
}
```

### Data Flow: Research → PPT

The PPT generation prompt receives three data sources to ensure quiz and market intelligence content is grounded in real research:

```
Research Agent
  ├── gap_summary (structured)  ──→  {gap_analysis_json}  ─┐
  ├── ChromaDB research chunks  ──→  {research_chunks}     ├──→ PPT Prompt → LLM
  └── (via Generate Agent)                                  │
Learning Guide (PDF)            ──→  {module_content}      ─┘
```

- `{gap_analysis_json}` — structured gap analysis (topic, severity, gaps, enrichments with sources)
- `{research_chunks}` — raw Tavily web search results from ChromaDB (actual job postings, trend data, statistics)
- `{module_content}` — the generated learning guide text (ground truth)

This ensures:
- **Quiz questions** test concepts the LLM structured as `gap_concepts` on the same slide
- **Market signal stats** are extracted from real web search results, not hallucinated
- **Source citations** name actual sources from the research data

### PPT Research References

| Research Area | Key Source | Finding | How We Use It |
|---------------|-----------|---------|---------------|
| Assertion-evidence slides | Garner & Alley (2013). *Technical Communication* | Full-sentence titles + visual evidence improve comprehension 15-20% | Topic slide titles are assertion sentences |
| Multimedia learning | Mayer (2009). *Multimedia Learning* | Words + pictures > words alone | Diagram helpers for each gap concept |
| Spatial contiguity | Mayer (2009) | Corresponding words and pictures near each other | Radar chart integrates all topic comparisons |
| Dual coding | Paivio (1986). *Mental Representations* | Verbal + visual encoding improves retention | Stats in exec summary + radar chart + market signal big stat |
| Refutational text | Tippett (2010). *Int. J. Sci. Math. Ed.* | Explicitly refuting misconceptions > presenting correct info | "Common Assumption" / "What's Actually True" callout boxes |
| Cognitive load (diagrams) | Sweller (1988). *Cognitive Science* | Diagrams externalize relationships, reducing extraneous load | Process flow, comparison, concept map (tree layout) |
| Graphical perception | Cleveland & McGill (1984). *JASA* | Shape/area differences pre-attentively perceived | Radar chart polygon gap is immediately visible |
| Coherence principle | Mayer (2009) | Exclude extraneous material | 1-sentence curriculum anchor, no "gap" language |
| Segmenting principle | Mayer (2009) | Content in learner-paced segments | Each concept is a self-contained card |
| Retrieval practice | Dunlosky et al. (2013). *Psych. Sci. in Public Interest* | Highest-utility learning technique | Quiz/Reflection slide with A-D options per topic |
| Metacognitive prompts | Guo (2022). *J. Computer Assisted Learning* | Reflection enhances self-regulated learning | Gold reflection prompt on each quiz slide |
| Relevance framing | Patall et al. (2023). *Frontiers in Psychology* | Career relevance drives autonomous motivation | Market Intelligence Spotlight with "What This Means For You" |
| Goal-setting | Locke & Latham (2002). *American Psychologist* | Concrete process increases follow-through | Recommendations process flow diagram |
| Visual accessibility | Hegarty & Waller (2005). *Cambridge Handbook* | Visual representations benefit diverse learners | Diagrams make abstract concepts accessible |
| Growth mindset framing | Dweck (2006). *Mindset* | Opportunity framing > deficit framing | All content frames as learning opportunities, never deficiencies |
| Personalization | Mayer (2009) | Conversational "you" language improves transfer | All slides use direct address ("You already know...") |

---

## Video Script Overhaul: PPT-Aligned Per-Topic Gap Teaching Videos

### The Problem with the Previous Video Design

The original video system generated a **single combined script** from all PPT slides, producing one long video (`gap_analysis_script.txt`). This violated multiple research-backed principles:

| Issue | Impact |
|-------|--------|
| **One long video for all topics** | Violates the 6-minute engagement cliff (MIT MOOC study: 6.9M sessions showed sharp attention drop after 6 minutes) |
| **Script reads slide text** | Violates Mayer's Redundancy Principle — presenting identical text in speech and on-screen reduces learning |
| **No hook or engagement structure** | First 3 seconds are critical for retention (Brandefy research); the old script opened with flat summaries |
| **No retrieval practice** | Zero embedded questions or pauses — entirely passive viewing |
| **No misconception correction** | Students leave with the same incorrect mental models |
| **Generic tone** | Formal, impersonal language; Mayer's Personalization Principle shows conversational "you" language improves transfer test scores |

### New Design: One Video Per PPT Topic Slide

**Critical design principle:** Each video script is **aligned with its PPT topic slide**. The PPT slide defines the structure — which topics, which gap concepts, in what order. The actual teaching content is drawn from three sources:

1. **ChromaDB vector store** — semantic retrieval from `curriculum` and `research` collections for the specific topic
2. **PDF module content** — the generated learning guide text (ground truth)
3. **Research gap summary** — structured gap analysis data

One PPT topic slide = one video script = one 2-5 minute video. The student can watch standalone OR alongside the matching PPT slide.

### 6-Section Spoken Structure

Every video script follows this research-backed structure:

| Section | Duration | Words | Research Basis |
|---------|----------|-------|----------------|
| **Hook** | 10-15s | 30-45 | First 3s critical (MIT); curiosity gap (Loewenstein) |
| **Anchor** | 15-20s | 45-60 | Schema activation (Gagne Event #3); uses PPT `curriculum_anchor` |
| **Teach the Gap** | 2-3 min | 300-450 | Segmenting + Signaling (Mayer); worked examples (Sweller); follows PPT `gap_concepts` order |
| **Misconception** | 20-30s | 60-90 | Refutational text effect (Tippett 2010); rephrases PPT `misconception.wrong` → `misconception.right` |
| **Retrieval Prompt** | 10-15s | 30-45 | Testing effect (Roediger & Karpicke 2006) |
| **Takeaways** | 20-30s | 60-90 | Recency effect + summary (Mayer) |

### Hook Types (HOOK_EXAMPLES constant)

Five proven hook formulas the LLM selects from based on the topic:

1. **Curiosity Question:** "What if I told you most graduates can't do X?"
2. **Scenario:** "Imagine you're on your first day as a [role], and..."
3. **Statistic:** "80% of job postings require Y, but only 20% of curricula cover it."
4. **Misconception:** "Most students think X works like Y. Here's why that's wrong."
5. **Value Promise:** "In the next 3 minutes, you'll learn the one concept that..."

### How the Three Sources Map to the Script

| Source | Role | What It Provides |
|--------|------|------------------|
| **PPT topic slide** (alignment) | Structure & ordering | `gap_concepts` (what to teach and in what order), `severity` (urgency framing), `curriculum_anchor` (what students already know), `misconception` (wrong→right) |
| **ChromaDB curriculum chunks** (vector retrieval) | Teaching content | Semantically retrieved chunks from original curriculum documents — accurate definitions, context, source material |
| **ChromaDB research chunks** (vector retrieval) | Teaching content | Semantically retrieved web search results, industry data, enrichments — real-world context |
| **PDF module content** (ground truth) | Teaching content | The generated learning guide text — synthesized explanations, examples, concept breakdowns |
| **Research/gap data** (structured) | Teaching content | Structured gap analysis — severity scores, specific gaps identified, recommendations |

### Complement-Not-Duplicate Strategy

The video script deliberately avoids reading slide content verbatim. Instead:

- When a slide has a **diagram**, the script references it: *"If you're looking at the slide, you can see the process flow — let me walk you through what each step actually means..."*
- The script follows the same `gap_concepts` ORDER as the PPT slide so watching alongside feels synchronized
- The script **teaches** (explanations, examples, context) while the slide **shows** (diagrams, definitions, visual evidence)

This follows Mayer's Redundancy Principle: presenting the same information simultaneously in text and speech reduces learning. The video and slide should complement each other, not duplicate.

### Prompt Design

Two prompts handle different paths:

**`SCRIPT_FROM_SLIDES`** (primary path — PPT available):
- Receives a single PPT topic slide as JSON (not the entire presentation)
- Receives ChromaDB curriculum and research chunks for the topic
- Receives PDF module content and structured gap analysis
- Produces a 300-750 word spoken script following the 6-section structure

**`MODULE_TO_SCRIPT`** (fallback — no PPT available):
- Receives module markdown and ChromaDB chunks
- Same 6-section structure, but without PPT-specific alignment fields

### Data Flow

```
Before (single combined video):
  slide_data (all topics) → 1 script → gap_analysis_script.txt → 1 video

After (PPT-aligned per-topic videos):
  PPT slide_data.topic_slides[0..N]  ← STRUCTURE
      + ChromaDB store.query()         ← RETRIEVAL
      + PDF modules_content            ← GROUND TRUTH
      + Research gap_summary           ← ENRICHMENT
      ↓ (parallel ThreadPoolExecutor)
  _generate_script_for_topic(topic_0) → script_0
  _generate_script_for_topic(topic_1) → script_1
  ...
      ↓
  01_Topic_Name_slide.txt → 01_Topic_Name_slide.mp4
  02_Another_Topic_slide.txt → 02_Another_Topic_slide.mp4
```

### Output Naming Convention

All video files include a `_slide` suffix to indicate PPT alignment:

```
outputs/{timestamp}_videos/
├── 01_Topic_Name_slide.mp4
├── 02_Another_Topic_slide.mp4
└── scripts/
    ├── 01_Topic_Name_slide.txt
    └── 02_Another_Topic_slide.txt
```

### Video Provider Architecture

The system supports HeyGen (primary) with Synthesia as a scaffold for future use:

- **HeyGen**: Full implementation — video generation, polling, download
- **Synthesia**: Scaffold stubs with `NotImplementedError` — documents the API contract differences (auth header, payload structure, no separate voice_id)
- Provider dispatch in `_process_single_video` routes to the correct client based on `settings.video_provider`

Configurable tuning parameters:
- `video_avatar_emotion`: Default "Friendly" — research shows enthusiastic delivery improves engagement
- `video_avatar_speed`: Default 1.05 — slightly faster speech conveys energy without sacrificing comprehension

### Video Research References

| Research Area | Key Source | Finding | How We Use It |
|---------------|-----------|---------|---------------|
| Engagement cliff | MIT MOOC study (6.9M sessions) | Attention drops sharply after 6 minutes | Target 2-5 min per video |
| First impressions | Brandefy video retention research | First 3 seconds determine whether viewers stay | 5 proven hook types in HOOK_EXAMPLES |
| Personalization | Mayer (2009). *Multimedia Learning* | Conversational "you" language improves transfer scores | All scripts use contractions and direct address |
| Redundancy | Mayer (2009) | Identical text + speech reduces learning | Video complements slides, doesn't read them |
| Segmenting | Mayer (2009) | Smaller segments improve comprehension | Per-topic videos, not one long combined video |
| Signaling | Mayer (2009) | Verbal cues organize information | "The key insight here is..." transition phrases |
| Coherence | Mayer (2009) | Extraneous material hurts learning | No URLs, tangents, or "further reading" in video |
| Conversational tone | Springer (2024) meta-analysis | Students perform better on transfer tests | Natural contractions, direct questions to viewer |
| Refutational text | Tippett (2010). *Int. J. Sci. Math. Ed.* | Explicitly refuting misconceptions > presenting correct info | Misconception section in every script |
| Testing effect | Roediger & Karpicke (2006). *Psych. Science* | Self-testing improves long-term retention | Retrieval prompt: "Pause and think about..." |
| Schema activation | Gagne Event #3 | Connect new to known before teaching | Anchor section uses `curriculum_anchor` from PPT |
| Worked examples | Sweller (1988). *Cognitive Science* | Step-by-step examples reduce cognitive load | Gap concepts taught with walkthrough explanations |
