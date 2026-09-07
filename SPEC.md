# SPEC.md — Programme Relevance Audit (HE product line)

<!-- Produced by /proto-spec from DOMAIN.md. BDD acceptance criteria — the stakeholder alignment
     gate before build. Scenarios become test names and assertions verbatim. -->
**Date:** 2026-09-07 · **Prerequisite:** `DOMAIN.md` (confirmed 2026-09-07) · **Ubiquitous language:** verbatim from DOMAIN.md

## Features (5 — cap reached)

| # | Feature | Domain context |
|---|---------|----------------|
| F1 | Labour-market-grounded gap analysis | **CORE** — Labour-Market Data + Audit & Gap Analysis |
| F2 | Programme Relevance Report (cold funnel) | Supporting — Funnel & Prospecting |
| F3 | Evidence pack compilation & issuance | **CORE** — Audit & Gap Analysis |
| F4 | Remediation draft generation | Supporting — Remediation Generation (reuse of existing Generate + quiz graph) |
| F5 | Remediation approval workflow | Supporting — Approval & Governance |

---

## F1 — Labour-market-grounded gap analysis

An audit run produces a severity-graded gap analysis for one programme version, and at audit
depth every gap claim is grounded in countable live vacancies.

### Scenario 1.1 — Vacancy-grounded claims at audit depth

- **Given** a validated curriculum has been ingested as a programme version with provenance `validated`
- **When** an audit run at evidence depth `vacancy_counted` completes the severity-graded gap analysis
- **Then** every gap claim names a missing skill, carries a severity grade of `critical`, `moderate`, or `minor`, and traces to at least one vacancy source showing a countable number of live vacancies

### Scenario 1.2 — Qualitative cold runs stay qualitative

- **Given** a public programme spec has been ingested as a programme version with provenance `public`
- **When** an audit run at evidence depth `qualitative` completes the severity-graded gap analysis
- **Then** every gap claim carries a severity grade, and the report is clearly marked as qualitative labour-market grounding rather than vacancy-counted evidence

### Scenario 1.3 — Ungrounded claims downgrade the run, never fabricate

- **Given** an audit run at evidence depth `vacancy_counted` has produced gap claims
- **And** one gap claim could not be matched to any vacancy source
- **When** the severity-graded gap analysis is finalised
- **Then** the ungrounded gap claim is excluded from vacancy-counted evidence and the run is flagged as downgraded to qualitative depth for that claim

### Scenario 1.4 — Labour-market grounding is current

- **Given** an audit run is starting the labour-market research stage
- **When** vacancy sources are attached to gap claims
- **Then** every vacancy source records its retrieval date so the evidence pack shows how current the labour-market grounding is

## F2 — Programme Relevance Report (cold funnel)

A prospect drops a public programme spec into the one-click funnel and receives a branded
Programme Relevance Report before any sales conversation — public data only, no DPIA, no
security review, no institutional data.

### Scenario 2.1 — One-click cold report

- **Given** a prospect has submitted a public programme spec through the cold funnel
- **When** the pipeline finishes
- **Then** a branded Programme Relevance Report is delivered containing severity-graded gaps, named missing skills, and three example modules

### Scenario 2.2 — Cold runs touch public data only

- **Given** a prospect has submitted a public programme spec
- **When** the cold report is generated
- **Then** the report is produced exclusively from public data and the prospect is never asked for the institution's validated curriculum, personal data, or any data-sharing agreement

### Scenario 2.3 — Cold funnel cost is capped

- **Given** the cold funnel produces a free artefact per prospect
- **When** a cold report run executes
- **Then** the run is restricted to the cheapest model tier so the per-prospect cost stays within the funnel budget

### Scenario 2.4 — Report delivered before the first conversation

- **Given** a cold report run has completed successfully
- **When** the Programme Relevance Report is ready
- **Then** it is deliverable to the prospect before any sales conversation has taken place

## F3 — Evidence pack compilation & issuance

For a paid Programme Relevance Audit, every gap claim is compiled into an evidence pack a
validation panel can audit — countable vacancies plus reproducible L1/L2 eval scores — and the
pack cannot be altered once issued.

### Scenario 3.1 — Every claim traceable

- **Given** an audit run at evidence depth `vacancy_counted` has completed a severity-graded gap analysis
- **When** the evidence pack is compiled
- **Then** every gap claim in the pack traces to at least one vacancy source with a countable number of live vacancies

### Scenario 3.2 — Eval scores attached and reproducible

- **Given** an audit run has completed with eval framework scores
- **When** the evidence pack is compiled
- **Then** the pack carries the L1 structural checks and L2 LLM-judge scores for the run, so a quality committee can see a measured, reproducible score for the generated material


### Scenario 3.3 — Immutable once issued

- **Given** an evidence pack has been issued to the programme team for the review panel
- **When** anyone attempts to change a gap claim, vacancy count, or eval score in the issued pack
- **Then** the issued pack is unchanged, and any corrected analysis requires a new audit run

### Scenario 3.4 — Audit delivered to the review panel

- **Given** a paid Programme Relevance Audit has completed for one programme
- **When** the audit is delivered
- **Then** the programme team receives the staff-facing deck and the evidence pack together as the audit deliverable

## F4 — Remediation draft generation

From one run, the pipeline produces the remediation bundle — study guide, gap-analysis deck,
narrated video, and Bloom's-tagged quizzes — always positioned as a draft for academic
approval, never finished teaching.

### Scenario 4.1 — Full bundle from one run

- **Given** an audit run has completed for a programme with an active licence
- **When** remediation is generated
- **Then** a remediation draft exists containing a study guide, a gap-analysis deck, a narrated video, and a set of Bloom's-tagged quizzes

### Scenario 4.2 — Quizzes tagged across Bloom's levels

- **Given** remediation has been generated for a programme
- **When** the quizzes are inspected
- **Then** every quiz question carries a Bloom's level tag drawn from the six Bloom's levels

### Scenario 4.3 — Always a draft, never finished teaching

- **Given** remediation has been generated for a programme
- **When** the remediation draft is presented to the programme team
- **Then** it is labelled as a draft for academic approval and cannot be published in that state

## F5 — Remediation approval workflow

A single named AI Lead approves or rejects the remediation draft. Approval unlocks delivery;
rejection triggers a full regeneration. Nothing ever publishes automatically.

### Scenario 5.1 — Approval unlocks delivery

- **Given** a remediation draft has been submitted for approval
- **When** the named AI Lead approves the draft
- **Then** the approved material becomes deliverable to the programme team

### Scenario 5.2 — Rejection triggers full regeneration

- **Given** a remediation draft has been submitted for approval
- **When** the named AI Lead requests a revision
- **Then** a new remediation draft is regenerated in full and submitted again for approval

### Scenario 5.3 — Nothing publishes without approval

- **Given** a remediation draft exists that has not been approved by the AI Lead
- **When** any delivery or publication of the material is attempted
- **Then** the material is not delivered and remains in the draft-for-approval state

### Scenario 5.4 — Single named approver

- **Given** a remediation draft has been submitted for approval
- **When** someone other than the named AI Lead attempts to approve it
- **Then** the approval is not accepted and the draft remains unsubmitted-for-delivery

---

## Out of Scope (deferred with reasons)

| # | Item | Reason deferred |
|---|------|-----------------|
| 1 | **Licence & quota enforcement (system-level)** | v1 sales are hand-held (dept card / AI Pilot Fund, offline). The Licence invariant stands in DOMAIN.md, but enforcement is operational (you only run what was sold) until self-serve purchasing exists. Building quota machinery now is plumbing before the first paying client. |
| 2 | **Curriculum Relevance Index / SectorIndex** | Invariant 7 (aggregate-only, consent rule) is unwritten — publishing cross-institution benchmarks without a consent/anonymisation rule is a legal risk, not a feature. Institutional tier ships only after 2 referenceable departments anyway. |
| 3 | **LMS delivery integration** | `MaterialPublishedToLMS` has no mechanism today (SCORM export unbuilt, v0.6 next-step). v1 fulfils approved material by direct delivery; LMS integration is a Dept-licence renewal-time feature. |
| 4 | **Payment/checkout automation** | Payment is commercial bookkeeping, not a system gate (confirmed in /domain-model interview). The audit is never discounted to zero — enforced in the sales motion, not in code. |
| 5 | **Fine-grained revision & committee approval** | Coarse regenerate-on-reject with a single AI Lead is the confirmed decision; per-module `SectionRevised` and multi-stage approval are deferred until real academics force finer grain. |

## Carried-forward hotspots (build-time decisions, not acceptance criteria)

- ⚡ **Adzuna integration shape** — new service in `backend/services/` vs normalizer on Tavily output; decide at build time. F1 scenarios are written integration-shape-neutral.
- ⚡ **Evidence pack vs real validation-panel requirements** — needs a `docs/research/` note before the pack schema is frozen; F3 scenarios cover what the report implies, not the full panel checklist.

## Status

**Confirmed by user 2026-09-07** — all 19 scenarios across F1–F5 accepted as the definition
of done. Gate passed. Next: `/clear`, then build (`/proto-build`).
