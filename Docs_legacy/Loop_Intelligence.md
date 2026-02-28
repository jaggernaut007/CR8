> **DEPRECATED** — This file has been superseded by the new documentation site at `docs/`. See `docs/design/strategic-overview.md` for the current version.
>
> This file is kept for reference only and will be removed in a future cleanup.

---

# CR8 Loop Intelligence — Implementation & Strategy Brief
## Doc file to summarise technical implementation such that the strategic roadmap can be built by the busniess agent(not present in the codebase) without needing to read through all the code. Should also include a summary of the tech stack, current status, and next steps.
**Last Updated**: 2026-02-27

---

## What CR8 Is

CR8 is a 3-agent AI pipeline that transforms university curriculum materials (PDFs, slides) into market-enriched learning guides. The core thesis: **curriculum in, industry-contextualized learning content out**.

```
Curriculum PDFs → [Ingest Agent] → [Research Agent] → [Generate Agent] → Learning Guide PDF
```

Built with LangGraph, OpenAI, ChromaDB, Tavily, fpdf2, and FastAPI. The prototype is fully operational as both a CLI tool and a web application deployed on GCP Cloud Run.

---

## Current Implementation Status

The prototype is **complete and deployed**.

### The 3-Agent Pipeline (Working)

**Ingest Agent** — Parses uploaded curriculum files (PDF/PPTX), uses GPT-5-nano to summarize each file in parallel (with map-reduce for files >15K chars), extracts 10-25 structured topics (with key techniques, domain context, and a curriculum scope boundary), chunks and embeds everything into ChromaDB's `curriculum` collection. Produces a topic list and a one-sentence `curriculum_scope` that constrains all downstream agents from drifting off-topic.

**Research Agent** — Takes each topic and runs two parallel Tavily web searches per topic (job skills/applications + industry trends/alternatives), retrieves matching curriculum chunks from ChromaDB, feeds all of it to GPT-5-mini for structured gap analysis (JSON mode) with severity rating (critical/moderate/minor), and stores enrichments in ChromaDB's `research` collection. All topics researched concurrently via ThreadPoolExecutor.

**Generate Agent** — Retrieves context from both ChromaDB collections for each topic (cached once, reused across generation and script stages), looks up its gap analysis, and uses severity-based model routing: critical topics get GPT-5.1 (premium), moderate/minor topics get GPT-5-mini. Each module is validated for required sections and minimum length with up to 2 retries. Generates learning modules in markdown with 7 sections: Curriculum Coverage, Identified Gaps, Learning Objectives (tagged Curriculum/Gap), Core Content, Industry Context, Key Takeaways (grouped Curriculum/Gap/Integration), and Further Reading. All modules generate in parallel, then compile into a chained output set: PDF (ground truth) → PPT (gap analysis slides structured around PDF chapters) → Video Script (synced to PPT slides with [SLIDE N] markers) → Video (via HeyGen API).

### Web UI (Working)

FastAPI web frontend with PDF upload (drag-and-drop), format selection with dependency chain (PDF always on, PPT optional, Script auto-enables PPT, Video auto-enables Script+PPT — disabled pending HeyGen keys), real-time progress tracking with stage labels and progress bar (polling every 3s), and file download. ProgressCapture intercepts stdout and parses stage prefixes with weighted stages: Ingest 15%, Research 50%, Generate 25%, Script 8%, Video 2%.

### Deployment (Working)

Dockerized on GCP Cloud Run (europe-west2). Single container with Gunicorn + Uvicorn, ephemeral ChromaDB, secrets from GCP Secret Manager. Scales to zero when idle (~$0 cost), cold starts in 30-60s. Configuration: 2 GiB RAM, 2 vCPU, 3600s timeout, max 1 instance.

### Test Coverage

144 tests passing (74 backend + 70 frontend). Covers file parsing, ChromaDB operations, PDF generation edge cases (Unicode, malformed markdown, special characters), run_job validation, all FastAPI endpoints, ProgressCapture thread safety.

---

## Tech Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Pipeline orchestration | LangGraph | State machine for agent coordination |
| LLM (extraction) | OpenAI GPT-5-nano | Summarization, topic extraction, PPT executive summary |
| LLM (analysis) | OpenAI GPT-5-mini | Gap analysis, moderate/minor module generation, PPT slides |
| LLM (generation) | OpenAI GPT-5.1 | Critical module generation, video scripts |
| Model routing | Severity-based (3-tier) | Nano/mini/premium tiers with task-specific temperature presets |
| Vector store | ChromaDB | Semantic search over curriculum and research |
| Embeddings | all-MiniLM-L6-v2 | Local, free, no API cost |
| Web search | Tavily API | Industry trends and job requirements |
| PDF extraction | PyMuPDF + python-pptx | Extract text from PDFs and slides |
| Slide image export | PyMuPDF + LibreOffice (planned) | Export slides as PNG for video backgrounds |
| Video composition | HeyGen API v2 (+ Elai.io fallback) | Avatar + slide scene-based video generation |
| PDF generation | fpdf2 | Compile learning guide PDF (rich text, code blocks) |
| PPT generation | python-pptx | Gap analysis PowerPoint with severity badges |
| Web framework | FastAPI + uvicorn | Async HTTP server for web UI |
| Concurrency | ThreadPoolExecutor | Parallel agent execution (max_workers=8) |
| Configuration | pydantic-settings | Type-safe env loading |
| Eval framework | DeepSeek-V3 + structural checks | Two-layer quality evaluation (L1 free + L2 ~$0.02/run) |
| Observability | LangSmith | Trace every LLM call |
| Deployment | Docker + GCP Cloud Run | Containerized, scales to zero |

---

## What's Proven

- Core concept validated: feed in lecture PDFs, get out a structured learning guide with industry context, gap analysis, and curated resources.
- Domain scoping via `curriculum_scope` prevents LLM drift across all agents.
- Parallelization across all three agents significantly reduces wall-clock time.
- Web UI provides usable end-to-end experience from upload to download.
- Cloud Run deployment is cost-effective and functional.
- **Chained output generation** works end-to-end: PDF → PPT → Script → Video, each building on the previous for cross-format consistency.
- **Multi-model routing** concentrates premium budget on critical topics (69% reduction in premium token usage).
- **Prompt optimization** is measurable: v1→v2 yielded +0.30 aggregate improvement (4.64 → 4.94) via the eval framework.
- **Evaluation framework** enables data-driven prompt iteration with statistical significance testing.

---

## Quality Infrastructure & Eval Framework

A two-layer evaluation system enables data-driven prompt iteration and regression detection — critical for maintaining output quality as the platform scales.

### Two-Layer Architecture

**L1 — Structural Checks (Free)**: 20+ automated checks on format and completeness — required sections present and in order, minimum content length, Bloom's taxonomy verbs in learning objectives, (Curriculum)/(Gap) tags, script word count limits, mandatory contractions in spoken-word scripts, no markdown artifacts in scripts. Runs instantly, no API cost.

**L2 — LLM Judge (~$0.02/run)**: DeepSeek-V3 evaluates outputs against weighted rubrics on a 1-5 scale. Four specialized judges: ModuleJudge (9 criteria including domain scope fidelity, pedagogical depth, factual grounding), PPTJudge (6 criteria including assertion-evidence titles, diagram appropriateness), ScriptJudge (7 criteria including hook effectiveness, spoken-word quality), and ConsistencyJudge (cross-output alignment).

### A/B Prompt Comparison

The system supports versioned prompt variants with full A/B comparison workflow:
1. Regenerate outputs using new prompt variant
2. Evaluate both variants (L1 + L2)
3. Compare with paired t-test for statistical significance (p < 0.05)
4. Detect regressions above configurable threshold

**Demonstrated result**: v1→v2 prompt optimization across generate and video agents yielded a +0.30 aggregate score improvement (4.64 → 4.94). Key fixes included enforcing (Curriculum)/(Gap) tags, script length limits, and mandatory contractions.

### Business Significance

- **Measurable quality**: Every prompt change can be quantitatively validated before deployment.
- **Regression prevention**: Automated detection ensures improvements in one area don't degrade another.
- **Cost efficiency**: L1 checks are free; L2 costs ~$0.02 per full evaluation run via DeepSeek-V3.
- **Scalable iteration**: Prompt registry supports unlimited versioned variants per agent. New versions are evaluated against the baseline before promotion to production.

---

## Strategic Roadmap

### Phase 1 — Immediate Next Steps

**React Frontend Upgrade** — Current single-page HTML is functional but limited. Replace with full React SPA for richer progress visualization, multi-job management, and better institutional UX.

**Prompt Iteration** — Content quality depends on prompt engineering. The GENERATE_MODULE prompt controls the quality ceiling. First optimization round complete (v1→v2, +0.30 aggregate improvement) via the eval framework. Continued refinement needed based on educator feedback and further A/B testing using the prompt registry.

**Video Generation with Slide Presentation** — The pipeline must produce 2-minute educational videos where an AI avatar presents over progressing slides extracted from the original curriculum materials (PDF/PPTX). The current implementation has a Script Agent (converts learning modules to spoken-word scripts via GPT-5-mini) and a Video Agent (submits scripts to HeyGen API for avatar-based video). However, the current system generates avatar-only videos on a white background with no slide integration.

The target architecture is: `Curriculum Slides → Slide Image Export → Script Generation with [SLIDE N] markers → Video API (avatar + slide backgrounds per scene) → Composited 2-min video`.

See **[Video_API_Research.md](Video_API_Research.md)** for the full evaluation of 10 video APIs, the recommended approach (extend HeyGen with slide backgrounds, Elai.io as fallback), cost projections, and the 6-step implementation plan.

### Phase 2 — Adaptive Intelligence Layer (6-12 months)

This is where CR8 transforms from a content generation tool into a **personalized learning platform**.

**PPO + DKVMN Hybrid System** — Dynamic Key-Value Memory Networks (DKVMN) for knowledge state estimation + Proximal Policy Optimization (PPO) for content selection. DKVMN maintains interpretable estimates of student mastery across 100-500 knowledge concepts. PPO optimizes what content to present next with a composite reward:

```
R_total = α * R_learning + β * R_engagement + γ * R_efficiency + δ * R_flow
```

Recommended weights: Learning 40-50%, Engagement 15-25%, Efficiency 10-20%, Flow state 15-25%.

**Cold Start Strategy** — ALEKS-style diagnostic assessment (20-30 questions, 15-20 min) combined with population priors from cohort data. Resolution confidence: 89%. Additional strategies: curriculum-based initialization, transfer learning, Thompson sampling.

**Multi-Agent Expansion** — Beyond the current 3 pipeline agents, the full platform adds 5 specialized agents:
1. Content Generation Agent
2. Assessment Agent
3. Analytics Agent
4. Quality Assurance Agent
5. Adaptation Agent (coordinates PPO + DKVMN)

### Phase 2 — Infrastructure Scaling

| Current | Migration Target | Reason |
|---------|-----------------|--------|
| Stable Baselines3 | RLlib (Ray) | Distributed training, 2-4 GPUs |
| Ephemeral ChromaDB | PostgreSQL + DynamoDB | Persistent, horizontally scalable |
| HeyGen API (avatar-only) | Elai.io or HeyGen scenes API (avatar + slides) | Native slide progression, reduced manual compositing |
| Manual slide compositing | ffmpeg/MoviePy post-processing pipeline | Full control over avatar + slide layout |
| ElevenLabs API | Self-hosted TTS (Coqui/OpenVoice) | Reduce API costs |
| Single Redis | Redis Cluster | High availability |
| Cloud Run | Kubernetes (AWS EKS) | Multi-node, GPU support |

Estimated monthly cost at 1,000-10,000 students: $2,000-3,000.

### Phase 3 — Production Scale (12-18+ months)

**Target**: 10,000-100,000+ students across 20+ UK universities.

- Multi-region Kubernetes deployment (US-East, UK, EU)
- LMS integration via LTI 1.3 (Canvas, Moodle, Blackboard)
- CDN for video delivery (CloudFront)
- Event streaming (Kafka) for interaction logging
- ONNX Runtime for optimized CPU inference
- WCAG 2.1 AA accessibility compliance
- Full A/B testing framework
- Published efficacy study in top education tech journal

---

## Key Dependencies & Risks

**API Cost Structure** — Pipeline is API-heavy (OpenAI + Tavily per topic). GPT-5.1 calls in Generate Agent are the primary cost driver at scale. Mitigation: 3-tier model routing (nano/mini/premium) with severity-based routing already reduced premium token usage by 69%. Further optimization possible via prompt compression and caching.

**Content Quality Ceiling** — Output quality bounded by prompt engineering and model capability. Domain scoping is effective and the eval framework enables measurable iteration (v1→v2 improved aggregate score by +0.30). Continued refinement from educator feedback and A/B testing is the primary lever for quality improvement.

**Single-Job Constraint** — Current architecture enforces one job at a time. Scaling to concurrent users requires job queuing, persistent storage (GCS), and multiple instances with shared state.

**Video API Dependency** — Video generation currently depends on HeyGen API. The slides-in-video upgrade has three implementation paths (HeyGen scene backgrounds, Elai.io native PPTX, or ffmpeg post-processing) to mitigate single-vendor lock-in. At scale, evaluate migration to Elai.io (native slide support) or open-source pipeline (SadTalker + ffmpeg) to reduce per-minute costs.

**Data Requirements for Adaptive Layer** — DKVMN needs 1,000+ students with 5K+ interactions. PPO needs 500+ students with 5K+ interactions. Until sufficient data, the adaptive system operates in cold-start mode.

---

## Market Context

AI video generation market: $614.8M (2024), projected $2.56B by 2032. Platform targets UK Higher Education — a market where ALEKS, Carnegie Learning MATHia, Khan Academy, and Squirrel AI have demonstrated effectiveness at scale, but none combine curriculum gap analysis with AI video generation and RL-based adaptation.

**Competitive advantage**: Hybrid PPO+DKVMN architecture + curriculum intelligence pipeline. Most competitors either optimize for engagement (MOOCs) or use static knowledge structures (ALEKS). CR8 aims to do both, with interpretable AI that educators can trust.

### Comparable Platforms

| Platform | Scale | Key Approach | Limitation for CR8's Market |
|----------|-------|-------------|---------------------------|
| ALEKS | Millions of students | Knowledge space theory, 25-30 question diagnostics | Static structure, no RL optimization |
| Duolingo | 500M+ learners | Half-life regression for spaced repetition | Language-only, not curriculum-aware |
| Squirrel AI | 24M+ students | Nano-level concept decomposition (10K+ micro-concepts) | Proprietary, China-focused |
| Carnegie MATHia | Major US districts | ACT-R cognitive tutoring, model tracing | Math-only, extensive domain engineering |
| Khan Academy | 500M+ accounts | Mastery-based learning, prerequisite maps | Hand-tuned mastery, primarily passive |
| Coursera/edX | 100M+ enrolled | Collaborative filtering for recommendations | Optimizes engagement, not learning outcomes |

---

## Budget Estimates

| Phase | Timeline | Budget | Key Costs |
|-------|----------|--------|-----------|
| Phase 1 (MVP) | 0-6 months | ~£30-40K | Salaries ~£24K, infra ~$3K/mo, video gen ~£1.5K |
| Phase 2 (Scale) | 6-12 months | ~£150-200K | Salaries ~£80K, infra ~$8K/mo, partnerships ~£40K |
| Phase 3 (Production) | 12-18+ months | ~£400-600K/year | Salaries £250K, infra $80-100K, R&D £50K |

---

## Immediate Action Items

### Technical (Pipeline & Quality)
1. **Slides-in-video implementation** — Extend file_parser.py with slide image export (PyMuPDF for PDF, LibreOffice CLI for PPTX), modify video_builder.py to use slide image backgrounds per scene. Script generation with [SLIDE N] markers is already implemented.
2. **Video API validation** — Test HeyGen scene background API with slide images to confirm avatar positioning and scaling works as expected; if insufficient, prototype Elai.io PPTX upload as fallback
3. **Prompt v3 iteration** — Use eval framework to develop and test v3 prompt variants based on educator feedback. Target areas: pedagogical depth (highest-weighted rubric criterion), practice/assessment quality
4. **Expand eval datasets** — Capture additional datasets beyond cs224n (e.g., computer science, engineering, business courses) to test prompt generalization across disciplines

### Business & Partnerships
5. Identify 3-5 UK university partners for MVP trial
6. Technical architecture review of PPO+DKVMN hybrid system
7. Prototype DKVMN on public student interaction datasets (Khan Academy, ALEKS)
8. Develop LMS integration API specification (LTI 1.3)
9. **React frontend upgrade** — Replace single-page HTML with full React SPA for institutional UX

## Open Research Questions

1. How quickly does PPO policy converge in an educational domain (interaction count)?
2. What is optimal reward function weighting (α, β, γ, δ) across different disciplines?
3. Can transfer learning reduce cold start below 10 interactions?
4. What learning outcome improvements are statistically significant vs. traditional adaptive systems?
