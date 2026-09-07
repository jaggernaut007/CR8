# TASK — Programme Relevance Audit (end-to-end HE product line)

Source input: `Docs/cr8-market-report.html` (Competitive & Market Research, CR8 · UK Higher Education, Aug 2026). Distilled via `/task-brief`; next reader: `/domain-model`.

## Product one-liner
CR8 shows a programme team exactly where their curriculum has drifted from what employers are hiring for — and then writes the teaching material that closes the gap, in days not a validation cycle.

## User (who, what job)
Called the **Associate Dean (Education)** / **Head of Curriculum or Quality** / **Director of Learning & Teaching**, and academic developers in Centres for Academic Practice.

- Job: periodic programme review, revalidation, PSRB accreditation, OfS quality conditions, graduate-outcome metrics — and right now, deciding which programmes survive portfolio rationalisation.
- Buying trigger: a review cycle with a closure or restructure decision attached. Every closure is preceded by a portfolio review requiring labour-market evidence, produced by hand today by an academic who resents the work. That artefact is what CR8 generates.
- MIT's Ad Hoc Committee on AI Use (13 Aug 2026) names the buyer with a job title: departmental **AI Leads** responsible for curricular adaptation, plus a **AI Pilot Fund** (sub-threshold departmental budget) that pays for exactly this work without procurement.

## Scope (agreed)
Programme Relevance Audit end-to-end = cold funnel **+** paid audit **+** severity-graded gap analysis **+** evidence pack **+** full remediation outputs. The whole HE product line.

Beachhead: Computing, Data, Business and Engineering programmes at post-92 / low-tariff institutions (highest closure rate, highest employability pressure, most measurable market drift).

## Screens / surfaces observed (from report, not UI mockups)
- **Cold-artefact funnel**: one-click pipeline — public programme spec in → branded "Programme Relevance Report" out. Severity-graded gaps, named missing skills, three example modules. Produced from public data *before the first conversation* (no DPIA, no security review, no data-sharing agreement).
- **Paid audit deliverable**: one programme — severity-graded gap analysis vs live market demand, staff-facing deck, evidence pack for the review panel. £4,000–£7,500 one-off.
- **Evidence pack**: gap claim traceable to countable live vacancies — requires UK structured job-posting data (Adzuna API) to beat Lightcast.
- **Remediation outputs** (the differentiator, "produces the remediation, not just the report"): study guide, gap-analysis deck for the programme team, narrated video, Bloom's-tagged quizzes — from one run. Human-in-the-loop: position as *draft for academic approval*, never finished teaching.

## Domain vocabulary (verbatim from the report)
programme review · portfolio rationalisation · revalidation · PSRB accreditation · OfS quality conditions · Programme Relevance Audit · Programme Relevance Report · severity-graded gap analysis · gap vs live market demand · evidence pack · curriculum relevance gap · labour-market grounding · AI Pilot Fund · AI Leads · evaluation framework · L1 structural checks · L2 LLM-judge · paired t-tests · model-agnostic · tiered model routing · open-source TTS · Chest agreement (Jisc collective licensing) · Curriculum Relevance Index · programme–occupation alignment

## Known constraints
- **Pricing**, keyed to procurement thresholds (Exeter/Kinston): Audit £4,000–£7,500 one-off (buyable on a department card, no tender); Dept Licence £18,000–£32,000/yr (≤~10 programmes, annual refresh, full content generation + LMS delivery); Institutional £55,000–£95,000/yr (only after 2 referenceable departments; accept a tender). Do NOT discount the audit to zero — a paid pilot is the only evidence the pain is real.
- **Positioning**: never sell "AI tutor" (free from OpenAI/Anthropic/Google); never headline "faster content generation" (Blackboard AI Design Assistant is free with the licence). Sell *knowing what to generate* — the external labour-market layer nobody else has. CR8 pipeline already does "curriculum in, market-enriched diagnosis + remediation out" — unsold in the UK.
- **Closest competitor**: Lightcast Skillabi (diagnoses the gap, hands you a to-do list, stops at the score). Plato (UK-native, curriculum-grounded) attacking the same insight — difference: Plato diagnoses gaps in *student understanding*; CR8 in the *curriculum itself against the labour market*. Keep razor-sharp.
- **Model agnosticism is a procurement story**, not just a margin story: tiered model routing + open-source TTS must be pitched as "no single commercial AI ecosystem," local-model capable.
- **Eval framework is a sales asset**: only vendor who can hand a quality committee a measured, reproducible score for generated material.
- **Buyer pain is real but sector is poor**: UK HE is the least solvent, slowest-procuring buyer. HE = credibility engine. (CPD line = cashflow, per report, but out of scope per agreed decision.)
- **91-day real-world pipeline shape** (report §09): cold funnel first (weeks 1–2), Adzuna gap-evidence (weeks 1–3), pilot-fund application template (weeks 2–4), 25 cold audits → 5 paid at £5k (weeks 2–6), sector report / Curriculum Relevance Index (weeks 4–10), Jisc/Chest + Universities UK channel (weeks 6–12). Sept is the critical inflection point.

## Open questions (for /domain-model to resolve)
1. Where in the existing CR8 pipeline (ingest → research → generate) does the Programme Relevance Report become a *distinct artefact* vs. a relabeled study-guide run? Output taxonomy per product tier (audit vs licence vs institutional).
2. How does the institute's *own validated curriculum* flow in and out of the gap-analysis so the AI Lead can approve the draft — approval workflow + versioning?
3. Adzuna UK job-posting data: schema mapping to existing research stage (Tavily-based) — new service in `backend/services/` or a normalizer on existing research output?
4. Which of the existing outputs map to "Bloom's-tagged quizzes" (exact Bloom's tags used today) and "narrated video" (Kokoro TTS pipeline) — reuse vs net-new?
5. Evidence-pack structure for a validation panel: what the report implies (gap score, named missing skills, vacancy counts, eval-framework L1/L2 scores) vs. what a UK validation panel actually requires.