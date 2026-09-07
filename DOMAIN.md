# DOMAIN.md — Programme Relevance Audit (HE product line)

<!-- Produced by /domain-model from TASK.md + EVENT_STORM.md. Next reader: /proto-spec.
     Gate: user confirms the core domain before /proto-spec proceeds. -->
**Date:** 2026-09-07 · **Sources:** `TASK.md`, `EVENT_STORM.md`, user interview (1 round)

## Bounded context

**Programme Relevance Audit** — one core capability, tightly named:

> Show a programme team exactly where their curriculum has drifted from what employers are
> hiring for, ground every gap claim in countable live vacancies, and produce the remediation
> material that closes the gap — as a draft for academic approval, never finished teaching.

One audit pipeline serves the whole product line (artefacts A–E). Artefacts differ by
**input provenance** (public spec vs validated curriculum) and **evidence depth** (qualitative
vs vacancy-counted + L1/L2 scores) — carried as fields on the run, not as separate pipelines.

## Ubiquitous language

Terms verbatim from the buyer's world (`TASK.md` §Domain vocabulary); these exact words appear
in code, events, and artefacts:

| Term | Meaning |
|------|---------|
| **Programme Relevance Audit** | The paid engagement: one programme, severity-graded gap analysis vs live market demand, evidence pack, staff deck (£4,000–£7,500, sub-procurement-threshold) |
| **Programme Relevance Report** | The cold-funnel artefact: branded report from public data only, delivered before any sales conversation |
| **Validated curriculum** | The institution's own approved curriculum, uploaded by the client — distinct from the public programme spec |
| **Provenance** | Where a programme version came from: `public` (cold funnel) or `validated` (client upload) |
| **Severity-graded gap analysis** | Per-topic gap classification: `critical` / `moderate` / `minor` (existing Research agent shape) |
| **Gap claim** | A single named missing skill/topic; at audit depth each claim must trace to ≥1 countable vacancy source |
| **Labour-market grounding** | The external evidence layer (Adzuna vacancy counts + Tavily enrichment) — "the layer nobody else has" |
| **Evidence pack** | Validation-panel artefact: gap score, named missing skills, vacancy counts, L1/L2 eval scores; immutable once issued |
| **Remediation draft** | Study guide + gap-analysis deck + narrated video + Bloom's-tagged quizzes from one run; always draft-for-approval |
| **AI Lead** | The single named approver of remediation drafts (MIT-named buyer role; also the pilot-fund budget holder) |
| **Licence** | Tier + quota record created after an offline sale: audit (1 programme) / dept (≤10 + annual refresh) / institutional |
| **Portfolio rationalisation** | The closure/restructure review cycle that is the buying trigger; the audit feeds its labour-market evidence requirement |
| **Curriculum Relevance Index** | Aggregate sector benchmark published across programmes/institutions (Jisc/UUK channel asset) |
| **Annual refresh** | Dept-licence entitlement: the audit cycle re-runs yearly on the licenced programmes |

## Entities & value objects

### Entities (aggregate roots marked ▸)

- **▸ Programme** — identity: programme id. Versioned; each version carries provenance.
  - **ProgrammeVersion** (child entity) — structured curriculum + `Provenance` + ingestion timestamp.
- **▸ AuditRun** — identity: run id. One run = one ProgrammeVersion + one EvidenceDepth.
  - **GapClaim** (child entity) — named missing skill, `SeverityGrade`, attached `VacancySource`s (≥1 required at audit depth), optional L1/L2 scores.
- **▸ EvidencePack** — identity: pack id. Compiled from a completed AuditRun; immutable once issued.
- **▸ RemediationDraft** — identity: draft id. Lifecycle: generated → submitted → approved *or* revision-requested (full regenerate) → published. Never auto-publishes.
- **▸ Licence** — identity: licence id. `Tier` + quota + annual-refresh flag; created manually after an offline sale (payment is bookkeeping, not a system event).
- **▸ SectorIndex** — identity: publication id. Aggregate-only benchmark across consented programmes.

### Value objects

- `SeverityGrade` — `critical | moderate | minor` (existing Research agent output)
- `BloomLevel` — six levels (existing quiz graph tags all six)
- `Provenance` — `public | validated`
- `EvidenceDepth` — `qualitative | vacancy_counted` (+ L1/L2 attachable at audit depth)
- `VacancySource` — Adzuna posting reference: occupation mapping, count, retrieval date

### Invariants

1. **Programme**: a version's provenance never changes after ingestion; public and validated curricula are distinct versions of the same programme.
2. **AuditRun**: cold runs (public provenance) are restricted to public data and the cheapest model tier — per-lead cost cap enforced by routing, not by trust.
3. **GapClaim** (audit depth): every claim traces to ≥1 countable `VacancySource`; claims without grounding downgrade the pack to qualitative depth.
4. **EvidencePack**: immutable once issued; carries the run's L1/L2 eval scores (the eval framework is a sales asset — reproducibility is the point).
5. **RemediationDraft**: no publish without `DraftApproved` by the single named AI Lead; `RevisionRequested` re-enters at generation (coarse loop — per-module revision deferred).
6. **Licence**: `ValidatedCurriculumUploaded` and remediation runs require an active licence with remaining quota; the audit is never discounted to zero (a paid pilot is the only proof the pain is real).
7. **SectorIndex**: aggregate-only reporting; no institution-identifiable data without explicit consent (consent rule unspecified — hotspot, must be written before institutional tier ships).

## Domain events

Past tense, ordered by product-line phase (full timeline in `EVENT_STORM.md`):

- **Funnel:** `ProgrammeSpecSubmitted` → `ProgrammeSpecIngested` → `LabourMarketResearched` → `MarketEvidenceAttached` → `ProgrammeRelevanceReportGenerated` → `ColdReportDelivered`
- **Audit:** `AuditPurchased` (offline sale recorded; creates Licence) → `ValidatedCurriculumUploaded` → `GapAnalysisProduced` → `EvidencePackCompiled` → `AuditDelivered`
- **Remediation:** `RemediationGenerated` → `DraftSubmittedForApproval` → `DraftApproved` | `RevisionRequested` (loops to `RemediationGenerated`) → `MaterialPublishedToLMS`
- **Licence/institutional:** `AnnualRefreshTriggered` → `PortfolioReviewEvidenceProduced` → `CurriculumRelevanceIndexPublished`

## Core vs. supporting

| | Context | Why |
|---|---------|-----|
| **CORE** | **Audit & Gap Analysis** | The paid core: provenance-aware ingestion, severity-graded gaps, evidence compilation. This is the artefact the buyer's review cycle demands. |
| **CORE** | **Labour-Market Data** | The differentiator — "knowing *what* to generate." Vacancy counting + occupation mapping nobody else (Lightcast stops at the score; Plato diagnoses students, not curricula) has. Deepest modelling investment goes here. |
| **Supporting** | Remediation Generation | The commercial differentiator ("produces the remediation, not just the report") but technically a *reuse* of the existing Generate pipeline + quiz graph — low new modelling risk. |
| **Supporting** | Funnel & Prospecting | Packaging of the core for pre-sale; same pipeline, public provenance, cost-capped. |
| **Supporting** | Approval & Governance | Coarse single-approver draft lifecycle; deliberately simple until real academics force finer grain. |
| **Supporting** | Licensing & Portfolio | Quota enforcement + refresh scheduling + sector index aggregation. Payment stays outside the system (confirmed with user: Licence is a system aggregate, sales are hand-held/offline). |
| **Generic** | Content rendering (PDF/PPT/video), TTS, eval harness, auth, LMS delivery | Existing platform capabilities; `MaterialPublishedToLMS` has no mechanism today (SCORM unbuilt) — v1 delivers artefacts directly. |

## Carried-forward hotspots (input to /proto-spec, not resolved here)

- ⚡ **Adzuna integration shape** — new service in `backend/services/` vs normalizer on Tavily output. Domain-neutral (Labour-Market Data context owns the contract either way); decide at spec time.
- ⚡ **Evidence pack vs real validation-panel requirements** — needs a `docs/research/` note before the pack schema is frozen (TASK Q5).
- ⚡ **SectorIndex consent rule** — invariant 7 names the rule; someone must write it.
- ⚡ **LMS delivery** — promised at Dept tier, unbuilt; keep `MaterialPublishedToLMS` as the last event but v1 fulfilment is manual/direct download.

## Status

**Confirmed by user 2026-09-07** — core-domain split (Labour-Market Data + Audit & Gap Analysis
as core; Remediation Generation as supporting reuse) approved. Ready for `/proto-spec`.

- `Tier` — `audit | dept | institutional`
- `LicenceQuota` — programme allowance per tier: 1 / ≤10 + refresh / tender-gated
