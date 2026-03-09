# CR8 Loop Intelligence v0.5

## Purpose of This Document

This document is the **single source of strategic truth** for CR8. It serves two consumers:

1. **The Strategy Agent** — An external agent that monitors the edtech market and decides which features CR8 should build next. This document gives it the context it needs: what CR8 is, what's built, what's planned, where CR8 sits competitively, and what the business model looks like. The strategy agent does not read code — it reads this document to understand CR8's capabilities, lifecycle stage, and market position so it can make informed prioritisation decisions.

2. **The Coding Agent** — Reads this document to understand the *why* behind implementation work. Knowing the strategic rationale (e.g., "flashcards exist because NoteGPT has them and universities expect them") helps the coding agent make better architectural decisions and trade-offs. Implementation specs live in `PM-Docs/roadmap.md` — this document provides the strategic frame, not the code-level detail.

**What this document is NOT:**
- Not a project management tracker (see `PM-Docs/todo.md`)
- Not a file-level implementation plan (see `PM-Docs/roadmap.md`)
- Not a sales document (see `PM-Docs/University_Pitch_Strategy.md`)

**Update cadence:** Refresh after each minor version bump (0.4 → 0.5 → 0.6). Keep under 400 lines.

**Last Updated**: 2026-03-09 (v0.5.2 — React SPA shell: Vite + Tailwind v4 + Tanstack Query + Vitest)
**Previous Version**: Loop Intelligence update 2026-03-06 (v0.5.1)

---

## What CR8 Is

CR8 is a multi-agent AI pipeline that transforms university curriculum materials (PDFs, slides) into market-enriched learning guides, quizzes, and slide-narrated videos. The core thesis: **curriculum in, industry-contextualised learning content out — then measure learning, and feed data back to improve content.**

```
Curriculum PDFs → [Ingest Agent] → [Research Agent] → [Generate Agent] →
  ├── Learning Guide PDF
  ├── Gap Analysis PPT
  ├── Video Script (with [SLIDE N] markers)
  ├── Narrated Slide Video (open-source TTS + ffmpeg)
  └── Interactive Quiz (planned — tests comprehension, records data)
       └── Feedback Loop → Agent improves future content
```

Built with LangGraph, OpenAI, ChromaDB, Tavily, fpdf2, FastAPI, React 19 + Vite 7 + Tailwind v4. Deployed on GCP Cloud Run. 795 backend tests + 42 Vitest + 5 Playwright E2E = 842 tests total.

---

## Development Lifecycle Stage

CR8 is a **late-prototype / early-product**. The content generation pipeline is complete and deployed. The learning measurement loop (quiz → feedback → regeneration) is partially built. No paying customers yet — targeting UK university pilots.

| Milestone | Status |
|-----------|--------|
| 3-agent pipeline (Ingest → Research → Generate) | Complete, deployed |
| PDF + PPT + Video Script output | Complete, deployed |
| Narrated slide video (Kokoro TTS, open-source) | Complete, deployed |
| GPU video service (NVIDIA L4, Cloud Run) | Complete, deployed |
| 3-tier video fallback (GPU → GPU fallback → CPU) | Complete, deployed |
| Web UI (FastAPI + Jinja2 prototype) | Complete, deployed |
| Security hardening (CORS, CSP, auth middleware) | Complete |
| Database layer (Neon PostgreSQL, 8 tables) | Complete |
| JWT authentication + legacy session dual-auth | Complete |
| Frontend route restructure (modular) | Complete |
| Test optimization (171s → 42s, pytest-xdist) | Complete |
| SPA catch-all + build pipeline ready | Complete |
| React SPA shell (Vite + Tailwind v4 + Tanstack Query, all pages wired to API) | Complete (v0.5.2) |
| React component tests (Vitest 42 tests) + Playwright E2E (5 auth flows) | Complete (v0.5.2) |
| Quiz Agent + quiz platform | Not started (v0.5) |
| Admin dashboard + analytics | Not started (v0.6) |
| Feedback loop (quiz → content regeneration) | Not started (v0.6) |
| Prompt v3 + SCORM export | Not started (v0.6) |
| Student engagement features (mind maps, flashcards, RAG chat) | Not started (v0.7) |
| Production readiness (job queuing, TTS upgrade) | Not started (v0.8) |
| LMS integration (LTI 1.3, WCAG, DPIA) | Not started (v0.9) |
| University pilot | Not started (v1.0) |

---

## Current Technical Capabilities

### The 3-Agent Pipeline

**Ingest Agent** — Parses uploaded curriculum files (PDF/PPTX), uses GPT-5-nano for parallel map-reduce summarisation, extracts 10-25 structured topics with key techniques and domain context, chunks and embeds into ChromaDB.

**Research Agent** — Runs two parallel Tavily web searches per topic (job skills + industry trends), retrieves matching curriculum chunks from ChromaDB, produces structured gap analysis (JSON mode) with severity rating (critical/moderate/minor). All topics researched concurrently.

**Generate Agent** — Severity-based model routing (critical → GPT-5.1, moderate/minor → GPT-5-mini). Generates learning modules in markdown with 7 sections. All modules generate in parallel, then compile into chained output: PDF → PPT → Video Script → Video.

### Video Pipeline

Two providers available:
- **Kokoro TTS** (primary) — Open-source, zero API cost. Two-phase: sequential TTS → parallel ffmpeg composition. Hardware-accelerated encoding (VideoToolbox/NVENC/QSV/AMF). ~34 min for a 5-topic, 33-slide job on Mac MPS. Output: H.264 MP4, embeddable and downloadable.
- **HeyGen** (dormant) — Code exists but is behind a feature gate. Avatar-only, no slide integration. Expensive. Kept for potential Phase 2 avatar overlay.

**Avatar overlay** (future): SadTalker/MuseTalk talking head composited over slides. Requires GPU (T4 minimum). Deferred to Kubernetes migration.

### Deployment

Three-container deployment on GCP Cloud Run, all scale to zero (~£0 idle):

- **CPU pipeline service** (europe-west2) — 3-agent pipeline + web UI + API
- **GPU video service — Primary** (europe-west4, NVIDIA L4) — fastest video (~2-3 min per job)
- **GPU video service — Fallback** (europe-west1, NVIDIA L4) — hot standby
- **CPU video service** (europe-west2, 8 vCPU) — slower but always available (~20-30 min)

Video data moves between services via GCS. Service-to-service calls authenticated with OIDC.

### Database & Auth (v0.5.1)

- **Neon PostgreSQL** — 8 tables (users, jobs, quizzes, quiz_questions, quiz_attempts, quiz_responses, chat_sessions, chat_messages), async via asyncpg. Schema includes Bloom's taxonomy, difficulty levels, one-attempt-only constraint, and pre-provisioned chat tables for v0.5.1.
- **Dual auth** — JWT (PyJWT + bcrypt) for API consumers + legacy session auth for existing web UI
- **Security** — SecurityHeadersMiddleware (CSP, X-Frame-Options, etc.), CORS locked to configured origins, AuthMiddleware on all non-public paths

---

## Strategic Roadmap

### Versioning
Commitizen semver. Minor bumps: 0.4 → 0.9, then 1.0 for university pilot release. Patches: 0.4.1, 0.4.2, etc.

### v0.4 — Kokoro TTS Video Pipeline (COMPLETE)
Local video generation with open-source TTS. GPU service offload. Security baseline. 3-tier video fallback.

### v0.5 — React Frontend + Quiz Platform (IN PROGRESS)
**Phase 1 (COMPLETE):** Database layer (Neon PostgreSQL), JWT auth, route restructure, Playwright E2E.
**Phase 1.5 (COMPLETE):** Test optimization (171s → 42s), pytest-xdist parallelism, SPA catch-all route, configurable upload limits (50MB), `make build-frontend` / `make e2e` / `make test-fast` targets, all docs migrated from pip to uv.
**Phase 2 (COMPLETE — v0.5.2):** Glassmorphism React SPA (React 19 + Vite 7 + Tailwind v4 + Tanstack Query). Five pages (Login, Dashboard, Upload, Progress, Results) wired to real API. JWT-aware fetch client and AuthContext. Vitest 42 component tests + Playwright 5 E2E tests. Stale Jinja2 tests removed.
**Phase 3:** Content viewers (PDF iframe, PPT carousel, HTML5 video player). Download PDF/PPT/Video only.
**Phase 4:** Quiz Agent (separate LangGraph workflow), one-attempt quizzes, Bloom's taxonomy, difficulty distribution.
**Infrastructure:** GitHub Actions CI, Dependabot planned alongside Phase 2.

### v0.6 — Admin Dashboard + Feedback Loop + Prompt v3 + SCORM
1. **Admin dashboard** — Recharts analytics, topic heatmaps, question analytics, user management, quiz editor.
2. **Feedback loop** — Quiz data → content regeneration with eval regression prevention. Per-topic, per-section improvement signals.
3. **Prompt v3** — New generation prompt variant, A/B eval against v2, feedback-informed. Pairs with feedback loop.
4. **SCORM export** — ZIP with imsmanifest.xml, self-contained HTML quiz. Direct LMS import. Procurement enabler.
5. **Evidence baseline** — Educator rubric ratings via admin dashboard, one-page evidence card.
6. **GitHub Actions CI** — ruff + pytest + pip-audit + Dependabot.
7. **Observability** — Structured logging (structlog), audit logging, RBAC, data retention policy.

### v0.7 — Student Engagement & Competitive Features
1. **Mind maps** — Mermaid.js from module JSON → SVG/PNG. Curriculum-grounded, not generic.
2. **Flashcards** — SM-2 spaced repetition, Bloom's tagged, Anki .apkg export.
3. **RAG chat** — ChromaDB retrieval + GPT-5-mini streaming. Students ask questions about course content. (DB schema pre-included in v0.5.)
4. **Student dashboard** — Topic mastery radar, flashcard progress, recommended study areas.

### v0.8 — Production Readiness
1. **Multi-user job queuing** — Cloud Tasks + GCS state. Replaces global single-job lock.
2. **TTS upgrade** — Evaluate Chatterbox (MIT, voice cloning) or CosyVoice 3 (multilingual). Kokoro stays as CPU fallback.
3. **Eval dataset expansion** — 3-5 domains beyond cs224n (Engineering, Health Sciences, Business).
4. **Content enhancements** — PPT citations, custom templates, multi-file batch processing, AI diagrams.

### v0.9 — LMS & Integration
1. **LTI 1.3** — SSO, grade passback, launch flow for Canvas/Moodle/Blackboard.
2. **Avatar video overlay** — SadTalker/MuseTalk talking head over slides (GPU service).
3. **Accessibility audit** — WCAG 2.1 AA (screen reader, contrast, keyboard nav, video captions).
4. **DPIA + DPA** — UK GDPR compliance for university pilot contracts.

### v1.0 — University Pilot Release
No new features — stabilisation and validation. All v0.5-v0.9 features deployed, CI/CD pipeline, LMS verified, DPIA/DPA signed off, runbook for university IT teams.

### Post-1.0 Phase 1 — Adaptive Intelligence (3-6 months)
- PPO + DKVMN hybrid for adaptive content selection from quiz data
- ALEKS-style diagnostic cold start (20-30 questions)
- Multi-agent expansion (Assessment, Analytics, QA, Adaptation, Content agents)

### Post-1.0 Phase 2 — Production Scale (6-12 months)
- Cloud Run → Kubernetes (GKE or AWS EKS)
- Event streaming (Kafka), CDN for video, multi-region
- Published efficacy study, international expansion

---

## Competitive Landscape & Positioning

### NoteGPT (Threat: Medium)
B2C AI study tool. Summarises YouTube/PDFs into notes, flashcards, mind maps, quizzes. $19.92/mo unlimited.

**What CR8 should adopt:** Mind maps, flashcards with SM-2 spaced repetition, RAG chat (all planned for v0.7).

**What CR8 already beats:** Curriculum grounding, institutional data ownership, feedback loop, B2B model, video generation.

### GravityWrite (Threat: Low)
Generic AI content mill with 250+ templates including education. Template-based, not curriculum-aware. No assessment, no video, no feedback loop.

**Positioning:** Demo-first sales showing the qualitative gap between template output and curriculum-grounded generation. No features to adopt.

### CR8 Competitive Moat (5 Pillars)

1. **Curriculum-grounded generation** — Ingests actual university PDFs/slides, not generic prompts
2. **Live industry research** — Tavily web search enriches content with current job market data
3. **Closed-loop improvement** — Quiz data feeds back into generation (no competitor has this)
4. **Institutional data ownership** — Student performance data belongs to the university
5. **B2B model** — Sells to institutions (£10-50K/year contracts) not individual students ($7-20/mo)

### Competitive Feature Response

| Feature | Why | CR8 Advantage Over Competitors | Target |
|---------|-----|-------------------------------|--------|
| Mind maps | NoteGPT has them; universities expect visual summaries | Curriculum-grounded, gap-analysis-enriched | v0.7 |
| Flashcards + SM-2 | NoteGPT has basic flashcards; SM-2 is proven pedagogy | Quiz data seeds difficulty, Bloom's tagged | v0.7 |
| RAG chat | Gap in all competitors | ChromaDB already populated by pipeline | v0.7 |
| Student dashboard | Gap in all competitors | Institutional + individual views | v0.7 |
| SCORM export | Gap in all competitors | Direct LMS import, procurement enabler | v0.6 |

---

## Business Model

**Target customer:** UK higher education institutions (HEIs).
**Revenue model:** B2B SaaS — £10-50K/year per institution depending on scale.
**Sales motion:** POC demo → Proof of Value (real module upload) → 6-12 week pilot → annual contract.
**Pricing advantage:** Video generation is £0 marginal cost (open-source). Quiz generation ~$0.01-0.02 per quiz via GPT-5-mini. Main cost is pipeline LLM calls.

See `PM-Docs/University_Pitch_Strategy.md` for detailed sales playbook.

---

## Key Dependencies & Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **API cost at scale** | Pipeline is API-heavy for content generation | Model routing (nano/mini/premium) already reduces cost; evaluate local models in Phase 3 |
| **Content quality ceiling** | Generated content may not meet educator standards | Feedback loop (v0.6) provides quantitative improvement signal; eval framework validates quality |
| **Video quality** | Kokoro TTS is near-commercial but not ElevenLabs-tier | Acceptable for MVP; upgrade path to Chatterbox/CosyVoice in v0.8 |
| **Quiz data cold start** | Feedback loop requires ~100+ students per topic | Until then, rely on manual educator feedback and eval framework |
| **Single-job constraint** | Only one pipeline job runs at a time | Quiz platform is independent and handles concurrent users; job queuing in v0.8 |
| **University procurement** | Long sales cycles (3-6 months), committee-driven | Three-stage engagement model (POC → POV → Pilot) with clear success criteria at each gate |

---

## Open Research Questions

These inform strategy agent decisions about feature prioritisation and technical direction:

1. Does Kokoro TTS quality meet educator expectations for lecture-style narration?
2. What is the optimal number of quiz questions per learning module? (5? 10? 15?)
3. How many quiz completions are needed before the feedback loop produces meaningful signals? (Hypothesis: 50-100 per topic)
4. Can quiz performance data initialise DKVMN knowledge state? (Reduces cold start for Phase 3 RL)
5. What quiz completion rate can we expect without gamification? (MOOC benchmark: 20-40%)
6. ~~Which SCORM version should CR8 target — 1.2 (widest support) or 2004 (richer data model)?~~ **Decided: SCORM 1.2** (widest LMS support, sufficient for MCQ quizzes, upgrade to 2004 only if a university partner requires it)
7. Can quiz question failure rates auto-generate targeted flashcards? (Cross-feature synergy)
8. How does NoteGPT's B2C retention compare to CR8's projected institutional retention?

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `PM-Docs/roadmap.md` | File-level implementation specs v0.4→v1.0, task lists, dependency graphs |
| `PM-Docs/todo.md` | High-level feature tracker (done / upcoming) |
| `PM-Docs/University_Pitch_Strategy.md` | Sales playbook, engagement model, pre-demo pack |
| `PM-Docs/Next_Steps_Roadmap.md` | Near-term execution priorities |
| `PROGRESS.md` | Session-level engineering progress |
| `docs/adr/` | Architecture Decision Records |
