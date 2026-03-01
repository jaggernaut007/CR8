# CR8 Next Steps Roadmap
**Last Updated:** 2026-03-01
**Status:** POC — targeting UK university partnerships

---

## Current POC State

The prototype is fully operational and deployed on GCP Cloud Run. The 3-agent pipeline (Ingest → Research → Generate) produces PDF learning guides, PPT gap analysis, and video scripts from curriculum PDFs. The web UI is password-protected and externally shareable with stakeholders.

**Working:** PDF, PPT, Video Scripts
**Not yet implemented:** Video rendering (HeyGen/Synthesia — API integration pending)

### March 2026 Hardening — Complete ✓

The pipeline underwent a full hardening pass covering:
- **10 bug fixes** across ChromaDB threading, eval harness math, progress parsing, and structural checks
- **Test suite expansion**: 144 → 362 tests (0 real API calls) with property-based testing (`hypothesis`), snapshot regression testing (`syrupy`), and full LangGraph graph integration tests
- **New test coverage**: all 3 pipeline agents, eval harness comparator/scorer, structural checks, and services are now fully tested with mock isolation

The codebase is now in a stable, well-tested state suitable for external demos and continued iteration.

---

## Immediate — Before First External Demo

### 1. Slides-in-Video
**What:** Extend the pipeline to produce actual videos with slide backgrounds, not just scripts.
**How:** Export PPT slides as images (PyMuPDF for PDFs, LibreOffice CLI for PPTX), then pass them as scene backgrounds in HeyGen's scene API. The `[SLIDE N]` markers in generated scripts are already implemented and sync-ready.
**Why now:** This is the highest-impact demo moment for universities. Static scripts are not compelling; a real AI avatar video with slides is.

### 2. React Frontend
**What:** Replace the vanilla JS single-page app with a React SPA.
**Priority features:** multi-job list, job history, cleaner progress UI, institutional branding.
**Why now:** The current UI is functional but will not meet institutional UX expectations. Universities judge product maturity by interface quality.

### 3. Prompt v3 Iteration
**What:** New `generate_v3.py` in `backend/evals/prompt_registry/variants/`.
**Target improvements:**
- Deeper pedagogical content (cite specific skills gaps with concrete examples)
- Better URL grounding for "Further Reading" (only verified URLs from research context)
- Stronger practice/assessment integration (at least 2 practice questions per module)
**How:** Use the existing eval framework. Run A/B comparison against v2 on the cs224n dataset.

---

## Short-Term — 1 to 3 Months

### 4. Multi-User Job Queuing
**What:** Replace the global single-job lock with Cloud Tasks + GCS-based state.
**Why:** The current architecture blocks all users when one job is running. Multiple university stakeholders demoing simultaneously will reveal this immediately.
**Approach:** Submit jobs to Cloud Tasks queue → worker reads from queue → state stored in GCS → frontend polls GCS for progress.

### 5. Elai.io Fallback
**What:** Test Elai.io's native PPTX upload API as an alternative to HeyGen scene backgrounds.
**Why:** Elai.io accepts PPTX files directly, which may produce better slide-video sync than manually passing background images to HeyGen.
**Action:** POC both approaches in parallel; pick the one with better visual output for the demo.

### 6. Expand Eval Datasets
**What:** Capture 3–5 domain datasets beyond `cs224n` using `capture_dataset.py`.
**Target domains:** Engineering (circuits, thermodynamics), Health Sciences (pharmacology, anatomy), Business (finance, operations management).
**Why:** Validates that prompt v2/v3 generalises across disciplines — critical for selling to multi-faculty universities.

### 7. Evidence Baseline
**What:** Internal study — have 2–3 educators rate a batch of pipeline outputs against a structured rubric.
**Output:** A one-page "evidence card" with preliminary learning quality scores.
**Why:** Universities will ask "how do you know this works?" Preliminary internal data beats nothing, and it opens co-research conversations.

---

## Medium-Term — 3 to 6 Months

### 8. DPIA and DPA
**What:** Commission a Data Protection Impact Assessment and a UK GDPR Article 28-compliant Data Processing Agreement.
**Why:** Non-negotiable before any university pilot. The ICO has increased scrutiny of EdTech data practices. A generic DPA will trigger red flags with university legal teams.
**Action:** Engage a UK-based data privacy solicitor; draft DPA covering curriculum content, student interaction data (future), and model training opt-outs.

### 9. LTI 1.3 Integration Spec
**What:** Document the integration pathway for Canvas, Moodle, and Blackboard.
**Why:** IT procurement at universities requires a credible integration roadmap. This does not need to be built; it needs to be plausibly planned.
**Deliverable:** A 2-page technical brief covering SSO (OAuth 2.0/SAML 2.0 via institution's IdP), grade passback (xAPI/SCORM), and LTI 1.3 launch flow.

### 10. Accessibility Audit
**What:** WCAG 2.1 AA compliance review of the web UI and all generated outputs.
**Scope:** Screen reader compatibility, colour contrast, keyboard navigation, captions on generated videos, transcripts.
**Why:** UK universities have legal obligations under the Equality Act 2010 and Public Sector Bodies Accessibility Regulations 2018.

---

## Long-Term Vision — 6 to 18 Months

The adaptive intelligence layer:

- **PPO + DKVMN Hybrid:** Dynamic Key-Value Memory Networks for student knowledge state estimation + Proximal Policy Optimization for personalised content selection
- **Cold Start:** ALEKS-style 20–30 question diagnostic for new students
- **5 Additional Agents:** Content Generation, Assessment, Analytics, QA, Adaptation
- **Infrastructure Scaling:** Kubernetes on AWS EKS, PostgreSQL + DynamoDB (replacing ephemeral ChromaDB), CDN for video delivery
- **LMS Integration:** Full LTI 1.3 for Canvas/Moodle/Blackboard

See `Loop/Loop_Intelligence.md` for full technical architecture and Phase 2/3 planning.

---

## Budget Reference

| Phase | Timeline | Indicative Budget |
|-------|----------|------------------|
| POC (current) | Now | API costs ~$50–100/month |
| MVP (Phase 1) | 0–6 months | ~£30–40K (salaries + infra) |
| Scale (Phase 2) | 6–12 months | ~£150–200K |
| Production (Phase 3) | 12–18+ months | ~£400–600K/year |
