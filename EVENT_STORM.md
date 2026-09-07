# EVENT_STORM.md — Programme Relevance Audit (HE product line)

<!-- Produced by /event-storm from TASK.md. Read automatically by /domain-model. -->
**Date:** 2026-09-07 · **Source:** `TASK.md`, `backend/pipeline/state.py`, `backend/prompts/research.py`, `backend/prompts/quiz.py`

## Key codebase discovery

The pipeline **already produces** a proto-version of the core artefact: the Research agent emits
per-topic severity-graded gap analysis (`critical|moderate|minor`) and the Generate agent renders a
"Gap Analysis PowerPoint" (`ppt_path`). Quizzes already carry all six Bloom's levels. What the product
line adds is (a) a **quantitative evidence layer** (countable live vacancies via Adzuna) on top of the
qualitative Tavily gap analysis, and (b) **audience-specific packaging** (prospect / programme team /
validation panel).

## Confirmed decisions (with user)

1. **Artefact taxonomy A–E holds.** A/B/C (cold report, paid audit, evidence pack) are **one audit
   pipeline** differentiated by *input provenance* (public spec vs validated curriculum) and *evidence
   depth* (qualitative vs vacancy-counted + L1/L2 scores) — not three pipelines.
2. **Remediation approval loop is coarse-grained with a single approver.** `RevisionRequested`
   re-enters at `RemediationGenerated` (full regenerate); one named AI Lead approves. Matches the
   "draft for academic approval, never finished teaching" positioning. (Rejected: per-module
   `SectionRevised` events, committee/multi-stage approval — deferred, see hotspots.)

## Artefact taxonomy

| # | Artefact | Tier | Input | Grounding | Audience |
|---|----------|------|-------|-----------|----------|
| A | Programme Relevance Report | Cold funnel (free) | Public programme spec | Tavily + Adzuna counts, public data only | Prospect, pre-conversation |
| B | Audit deliverable (gap analysis + staff deck) | Paid audit £4,000–£7,500 | Institution's validated curriculum | Adzuna live demand, per-topic severity | Programme team |
| C | Evidence pack | Paid audit | B + eval scores | Countable vacancies + L1/L2 reproducibility | Validation panel |
| D | Remediation bundle (study guide, deck, narrated video, Bloom's-tagged quizzes) | Dept licence | Approved curriculum | Draft-for-approval | Academics / AI Lead |
| E | Curriculum Relevance Index | Institutional | Aggregate across programmes | Sector benchmark | Jisc/UUK channel, marketing |

## Event timeline (ordered, past tense)

### Cold funnel (pre-sale, public data only — no DPIA, no security review)
1. `ProgrammeSpecSubmitted` — prospect drops a public programme URL/PDF into the one-click funnel
2. `ProgrammeSpecIngested` — spec parsed into structured curriculum (existing Ingest agent)
3. `LabourMarketResearched` — live vacancies pulled (Adzuna) + qualitative enrichment (Tavily)
4. `MarketEvidenceAttached` — gap claims linked to countable vacancy sources
5. `ProgrammeRelevanceReportGenerated` — severity-graded gaps, named missing skills, 3 example modules
6. `ColdReportDelivered` — branded report delivered before any sales conversation

### Paid audit (one programme, £4,000–£7,500, sub-procurement-threshold)
7. `AuditPurchased` — dept card / AI Pilot Fund; **never discounted to zero** (paid pilot is the only proof the pain is real)
8. `ValidatedCurriculumUploaded` — institution's own approved curriculum enters as a new Programme version
9. `GapAnalysisProduced` — severity-graded gaps vs live market demand (existing Research agent shape)
10. `EvidencePackCompiled` — each gap claim traceable to countable vacancies + L1/L2 eval scores
11. `AuditDelivered` — staff-facing deck + evidence pack handed to the review panel

### Remediation (the differentiator — "produces the remediation, not just the report")
12. `RemediationGenerated` — study guide + gap-analysis deck + narrated video (Kokoro) + Bloom's-tagged quizzes from one run (existing Generate + quiz graph)
13. `DraftSubmittedForApproval` — positioned as draft, never finished teaching
14. `DraftApproved` — single named AI Lead signs off → proceed to publish
15. `RevisionRequested` — AI Lead rejects → **full regenerate** (loop to event 12)
16. `MaterialPublishedToLMS` — approved content delivered (hard human gate; never auto-publishes)

### Licence / institutional (recurring)
17. `AnnualRefreshTriggered` — dept licence (≤~10 programmes) re-runs the audit cycle
18. `PortfolioReviewEvidenceProduced` — feeds closure/restructure decisions (portfolio rationalisation)
19. `CurriculumRelevanceIndexPublished` — aggregate sector report (marketing + Jisc/UUK channel asset)


## Aggregates (name → events → governing rule)

| Aggregate | Events | Core rule |
|-----------|--------|-----------|
| **Programme** | `ProgrammeSpecSubmitted`, `ProgrammeSpecIngested`, `ValidatedCurriculumUploaded` | Versioned: public spec and validated curriculum are different versions of the same programme; provenance recorded per version |
| **AuditRun** | `AuditPurchased`, `GapAnalysisProduced`, `MarketEvidenceAttached`, `ProgrammeRelevanceReportGenerated`, `AuditDelivered` | One run = one programme version + one evidence depth; cold runs restricted to public data |
| **EvidencePack** | `EvidencePackCompiled`, `EvidencePackIssued` (implied) | Every gap claim traces to ≥1 countable vacancy source; L1/L2 scores attached; immutable once issued |
| **RemediationDraft** | `RemediationGenerated`, `DraftSubmittedForApproval`, `DraftApproved`, `RevisionRequested`, `MaterialPublishedToLMS` | Never auto-publishes; coarse regenerate-on-reject; single named approver |
| **Licence** | `AuditPurchased`, `AnnualRefreshTriggered` | Tier → quota: audit = 1 programme; dept = ≤10 + annual refresh; institutional = tender only after 2 referenceable departments |
| **SectorIndex** | `CurriculumRelevanceIndexPublished`, `PortfolioReviewEvidenceProduced` | Aggregate-only reporting; no institution-identifiable data without consent |

## Hotspots ⚡

- ⚡ **Adzuna integration shape** — new service in `backend/services/` vs. a normalizer on existing Tavily research output? (TASK open Q3)
- ⚡ **Evidence pack vs. real panel requirements** — what the report implies (gap score, named skills, vacancy counts, L1/L2) vs. what a UK validation panel actually requires (TASK open Q5)
- ⚡ **`AuditPurchased` gating** — is payment a technical gate (blocks `ValidatedCurriculumUploaded`) or purely commercial bookkeeping? Affects whether Licence is a system aggregate or an external concern.
- ⚡ **Cold-run cost cap** — a free funnel artefact still burns LLM/Tavily/Adzuna spend per lead; where is the per-lead budget enforced (rate limit? cheaper model tier via existing model routing)?
- ⚡ **Deferred: fine-grained revision & committee approval** — coarse loop chosen now; per-module `SectionRevised` and multi-stage `ApprovalStageAdvanced` may be needed when real academics use it
- ⚡ **SectorIndex consent boundary** — aggregating audit results into a published index across institutions needs an explicit consent/anonymisation rule nobody has specified
- ⚡ **`MaterialPublishedToLMS` mechanism** — "LMS delivery" is promised at Dept Licence tier, but no LMS integration exists in the codebase today (SCORM export is a v0.6 next-step, unbuilt)

## Bounded context candidates

| Context | Events | Responsibility |
|---------|--------|----------------|
| **Funnel & Prospecting** | 1–6 | Turn public programme specs into branded cold reports at near-zero marginal cost; no PII, no institutional data |
| **Audit & Gap Analysis** | 7–11 | The paid core: provenance-aware curriculum ingestion, severity-graded gap analysis, vacancy-grounded evidence |
| **Labour-Market Data** | `LabourMarketResearched`, `MarketEvidenceAttached` | Adzuna/Tavily integration, vacancy counting, occupation mapping; the "external layer nobody else has" |
| **Remediation Generation** | 12, 16 | Reuse of existing Generate stage + quiz graph: guides, decks, narrated video, Bloom's-tagged quizzes |
| **Approval & Governance** | 13–15 | Human-in-the-loop draft lifecycle; versioning of approved material; audit trail for quality committees |
| **Licensing & Portfolio** | 7, 17–19 | Tiers, quotas, annual refresh, portfolio-review evidence, sector index aggregation |

**Context relationships:** Funnel and Audit share the Programme aggregate (public vs validated
versions). Labour-Market Data serves both Funnel (cheap) and Audit (deep). Remediation Generation is
downstream of Approval & Governance — nothing publishes without `DraftApproved`.

## Handoff to /domain-model

Open questions carried forward from TASK.md, now with storm context:
- Q1 → **resolved**: one audit pipeline, provenance + evidence-depth as state fields (taxonomy A–E above)
- Q2 → **partially resolved**: Programme is versioned with provenance; approval = coarse loop, single AI Lead; committee approval deferred as hotspot
- Q3, Q4, Q5 → open hotspots above
