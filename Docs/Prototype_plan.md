# Prototype Plan — Adaptive Learning System

## Goal

Prove the core concept: **curriculum in → market-enriched learning PDF out**. Keep it minimal. No sub-agents, no formal contracts, no production infrastructure.

---

## Tech Stack

- **Frontend**: ReactJS — single page with curriculum upload, progress indicator, and PDF download
- **Backend**: Python + Flask API
- **Agent Orchestration**: LangGraph
- **LLM**: OpenAI API
- **Vector Store**: ChromaDB (local, single instance with collection tags)
- **PDF Generation**: WeasyPrint or ReportLab
- **Observability**: LangSmith tracing

---

## Agents

Three agents in a linear pipeline. No sub-agents. Each agent is a single LangGraph node.

```
Curriculum Files
      │
      ▼
┌───────────┐    topic list
│  Agent 1  │──────────────┐
│  Ingest   │              │
└─────┬─────┘              │
      │                    │
      ▼                    ▼
  ChromaDB            ┌───────────┐
  [curriculum]        │  Agent 2  │
      │               │  Research │
      │               └─────┬─────┘
      │                     │
      │                     ▼
      │               ChromaDB
      │               [research]
      │                     │
      └──────────┬──────────┘
                 │
                 ▼
          ┌───────────┐
          │  Agent 3  │
          │  Generate │
          └─────┬─────┘
                │
                ▼
           PDF Output
```

### Agent 1: Ingest

**Input**: Curriculum files (PDFs, slides)
**Output**: Topic list + ChromaDB `curriculum` collection populated

1. Parse uploaded files and extract text
2. Use the LLM to extract a flat list of topics with brief descriptions
3. Chunk the content and embed into ChromaDB tagged as `curriculum`
4. Pass the topic list to Agent 2

### Agent 2: Research

**Input**: Topic list from Agent 1
**Output**: ChromaDB `research` collection populated + gap summary

1. For each topic, use web search tools to find:
   - Related job postings and required skills
   - Recent industry trends and developments
2. Compare findings against the curriculum content in ChromaDB — identify gaps (missing skills, outdated content)
3. For each gap, research and produce a short enrichment (definition, why it matters, key resources)
4. Store all research + enrichments in ChromaDB tagged as `research`
5. Pass a gap summary to Agent 3

### Agent 3: Generate

**Input**: Topic list, gap summary, access to both ChromaDB collections
**Output**: A structured learning material PDF

1. For each topic, retrieve relevant chunks from both `curriculum` and `research` collections
2. Use the LLM to generate a learning module with:
   - **Learning objectives** — what the student should know after this section
   - **Core content** — explanation of the topic drawn from curriculum
   - **Industry context** — market relevance, real-world applications, in-demand skills (from research)
   - **Key takeaways** — summary bullets
   - **Further reading** — curated links and resources
3. Compile all modules into a single PDF with:
   - Table of contents
   - Chapter structure (one chapter per topic)
   - Consistent formatting suitable for self-study

---

## Evaluation (Prototype-Level)

Keep it simple. LangSmith tracing is the primary tool — no formal eval frameworks yet.

| What | How |
|------|-----|
| **Does the pipeline complete?** | LangSmith traces — all 3 nodes finish without errors |
| **Are topics extracted correctly?** | Manual review — compare topic list against source curriculum |
| **Is the research relevant?** | Manual review — spot-check 5 topics for research quality |
| **Does the PDF make sense?** | Human read-through — is the output useful to a student? |
| **Where is time spent?** | LangSmith latency per node |

Formal evaluators (openevals, agentevals, LLM-as-judge, regression datasets) are added post-prototype once the core flow works.

---

## Development Approach

- **TDD**: Write a test for each agent's input → output before implementing
- **Iterate**: Get the pipeline end-to-end first (even with poor quality), then improve each agent
- **One vector DB**: ChromaDB with collection tags (`curriculum`, `research`) — no need for separate databases
- **Document as you go**: Inline comments where non-obvious, README with setup instructions

---

## Scope & Future Work

This prototype deliberately defers the following. Each is planned for post-prototype phases once the core pipeline is validated.

| Deferred | Why | When |
|----------|-----|------|
| **Video generation pipeline** (HeyGen API, TTS, post-processing) | Core product feature, but PDF proves the content quality first. Video adds cost and complexity without validating the intelligence layer. | Phase 2 — once content quality is proven |
| **Student-facing interaction loop** (assessment agent, adaptation agent, knowledge state tracking via DKVMN/PPO) | Requires RL infrastructure, student data, and a live learning environment. Separate system from the curriculum intelligence pipeline. | Phase 2-3 |
| **LMS integration** (LTI 1.3 for Canvas/Moodle) | Critical for institutional adoption, but not needed to prove the concept. | Phase 2 |
| **Multi-format output** (slides, quizzes, podcasts, interactive PDF) | PDF is sufficient to validate content quality. Other formats are rendering variations of the same content. | Phase 2 |
| **Content QA / fact-checking** (automated claim verification, SME review pipeline) | Important for production. For prototype, manual review of output is enough. | Phase 2 |
| **WCAG 2.1 AA accessibility** (captions, audio descriptions, contrast compliance) | Regulatory requirement for production. Not needed to prove core concept. | Phase 2 |
| **A/B testing framework** | Needed to measure learning effectiveness at scale. Prototype uses manual evaluation. | Phase 2 |
| **Formal evaluation framework** (openevals, agentevals, LLM-as-judge, regression datasets) | Valuable for CI/CD and quality gates. Prototype uses LangSmith tracing + human review. | Phase 2 |
| **UK HE curriculum alignment** (QAA subject benchmarks, TEF metrics) | Target market context. Prototype works with any curriculum to prove the pipeline. | Phase 2 |
