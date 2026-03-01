# CR8 University Pitch Strategy
**Last Updated:** 2026-03-01
**Target:** UK higher education institutions (HEIs)

---

## The Three-Stage Engagement Model

Do not treat everything as a "POC." Use staged language that universities understand. Each stage requires a defined commitment from both sides before it begins.

| Stage | Your Ask | Their Commitment | Duration |
|-------|----------|-----------------|----------|
| **POC** | Watch a demo, give structured feedback | 1 hour + written feedback | Week 1 |
| **POV** (Proof of Value) | Upload one real module, evaluate output quality | 2–3 hours over 2 weeks | Weeks 2–4 |
| **Pilot** | Run in a real module with students, co-evaluate | Signed pilot agreement + ethics approval | 6–12 weeks |

**Critical:** Before each stage, agree on what success looks like and what happens if criteria are met. A verbal "that looks interesting" is not a commitment.

---

## Pre-Demo Pack

Prepare all of these before the first outreach call. Do not wait to be asked.

| Document | Purpose | Primary Audience |
|----------|---------|-----------------|
| 2-page Product Overview (plain English, no jargon) | First-pass evaluation | Faculty, Dept Head |
| 1-page Pedagogical Rationale | Academic credibility | Faculty, VC Education |
| 1-page AI Transparency Card | Governance and ethics review | Ethics Committee, Academic Senate |
| Security Posture Summary | IT and cybersecurity review | IT, Cybersecurity team |
| GDPR Position Statement + DPA draft | Legal compliance | Data Protection Officer, Legal |
| LMS Integration Roadmap | Technical readiness | Learning Technologist, IT |
| Pilot Framework Proposal | Structured engagement plan | All stakeholders |

### What Each Document Must Include

**Pedagogical Rationale:** Map the tool's design decisions to learning science.
- Cite Mayer's Cognitive Theory of Multimedia Learning (why video + script is effective)
- Cite cognitive load theory (why gap analysis structures content for working memory)
- Explain how the "educator reviews and edits before generation" design preserves faculty authority
- Cite one or two relevant EdTech efficacy papers (EEF Teaching and Learning Toolkit is a credible reference)

**AI Transparency Card:** Answer these questions in plain language:
- Which AI models power the tool? (OpenAI GPT-5 family, DeepSeek for evals)
- What data does the system ingest? (curriculum PDFs — does not process student data in current POC)
- Who owns the generated content? (the institution / educator)
- Can outputs be used for academic assessment? (no — requires human review)
- What are the known limitations? (hallucination risk in "Further Reading" URLs, domain-specific accuracy variance)
- Is content used to train models? (no — explicitly prohibited in API terms)

---

## 45-Minute Demo Structure

### Minutes 0–5: Problem Framing (Not a Company Intro)

Open with their context. Reference something specific to the institution or their stated priorities. Lead with a question:

> "We've heard from lecturers that creating video content for blended learning takes between 4 and 8 hours per module. Is that consistent with what your team experiences?"

Never open with a company introduction slide. Academic audiences are trained to recognise vendor framing and will disengage.

### Minutes 5–15: The Core Workflow Demo

Demonstrate a single end-to-end workflow, live. Use their actual module materials if possible — ask for a module descriptor or lecture outline before the meeting.

**Show:**
1. Upload a curriculum PDF
2. Watch the pipeline extract topics and run gap analysis
3. View the generated learning guide (PDF)
4. Show the video script with `[SLIDE N]` markers
5. **Critically:** Show the editorial review step — the educator reads, edits, and approves the script before any video is generated

The editorial control step is the most important moment in the demo. Faculty need to see that they remain the academic authority. Lingering here builds trust.

### Minutes 15–25: Evidence and Trust

Do not leave evidence to a brochure. Dedicate a full 10 minutes explicitly to:
- One comparable institution case study (UK university preferred; US research institution acceptable)
- One learning quality data point (internal rubric scores from educator review are sufficient)
- Three dedicated slides: data handling, GDPR position, LMS integration roadmap

This section is not for selling. It is for preemptively removing the blockers that IT, Legal, and Ethics will raise after the demo if you do not address them here.

### Minutes 25–40: Guided Q&A

Do not ask "any questions?" — this produces silence or vague comments.

Ask targeted questions that surface buying criteria:
- *"What would need to be true about output quality for this to be useful in your department?"*
- *"Which modules would you most want to test this on first?"*
- *"If we ran a 12-week pilot, what would success look like from your perspective?"*
- *"Who else would need to be involved in a decision to pilot this — IT, Legal, the ethics committee?"*

The last question is critical. Map the full decision chain before leaving the room. Hidden veto-holders (DPO, IT security, academic senate) can kill a deal weeks later.

### Minutes 40–45: Concrete Next Step

Leave the room with one agreed action, an owner, and a date. Not "let's stay in touch."

Options to propose:
- Technical call with IT/Learning Technology team (within 1 week)
- POV scoping session — share one module descriptor, review output quality together (within 2 weeks)
- Co-research partnership discussion — joint evaluation study design (within 4 weeks)

---

## What Universities Evaluate (In Priority Order)

### 1. Pedagogical Alignment
Does this support or undermine the educator's role? Universities are not procuring software — they are making decisions about academic practice. Every feature will be assessed through this lens.

**Signals that build confidence:**
- Clear editorial control at every step
- Content grounded in curriculum, not generic AI output
- Explicit alignment with learning outcomes and Bloom's taxonomy
- The tool augments the educator, not replaces them

### 2. GDPR and Data Privacy
The ICO increased EdTech scrutiny in 2024–2025. The LSE's 2025 report on EdTech data practices found widespread concern about "thin contractual safeguards" in existing tools. Universities are now acutely aware.

**Non-negotiable requirements:**
- UK GDPR Article 28-compliant Data Processing Agreement (DPA) before any pilot
- Data Protection Impact Assessment (DPIA) or willingness to complete one jointly
- UK/EU data residency for any data stored server-side
- Explicit prohibition on using institutional content for model training
- Named Data Protection Officer contact

A generic DPA from a template will trigger immediate red flags. Commission a purpose-written one.

### 3. Evidence of Learning Outcomes
"How do you know this works?" is the question every faculty member and VC Education will ask.

**What counts as evidence (in decreasing credibility):**
1. Peer-reviewed study with pre/post learning measures (ideal but not required for POC)
2. Structured pilot with educator rubric scores and student feedback (acceptable for pilot proposal)
3. Internal evaluation with 2–3 educator raters (sufficient for POV stage)
4. Commitment to co-produce evidence during the pilot (acceptable at POC stage)

Reference the Education Endowment Foundation (EEF) methodology when proposing a pilot evaluation design. This signals institutional credibility.

### 4. LMS and System Integration
"Does this add another login, or does it work inside our existing infrastructure?"

UK HE LMS breakdown: Canvas (~43%), Moodle, Blackboard. The integration standard is LTI 1.3 with SSO via OAuth 2.0 or SAML 2.0 federated through the institution's identity provider.

For a POC, you do not need full LTI integration. You need a credible roadmap and a technical brief demonstrating you understand what's required.

### 5. Accessibility
UK universities have legal obligations under the Equality Act 2010 and the Public Sector Bodies Accessibility Regulations 2018. This is not optional.

**Minimum requirements before pilot:**
- WCAG 2.1 AA compliance for the web interface
- Captions on all generated video content
- Transcripts available for all audio
- Published Accessibility Statement

### 6. AI Governance and Transparency
Universities are building AI governance frameworks. They will ask:
- What AI models are used, and under what data terms?
- Who owns generated content — the institution, the educator, or the vendor?
- Can students use this tool? What are the academic integrity implications?
- What are the known failure modes (hallucination, factual error)?
- Is there a human-in-the-loop before content reaches students?

Proactively publish an AI Transparency Card (see Pre-Demo Pack above) to remove these questions before they are asked.

---

## Common Pitfalls

| Pitfall | Consequence | Prevention |
|---------|------------|------------|
| Using synthetic or cherry-picked demo data | Erodes trust; academic audiences spot selection bias | Ask for a real module descriptor before the meeting; use it in the demo |
| Demoing feature breadth | Faculty leave with vague capability impression, no mental model of fit | One workflow, done deeply; six features done superficially |
| Engaging only faculty | IT/Legal veto kills deals after demo | Engage IT and DPO in parallel from the first contact |
| Generic GDPR DPA | Legal red flag; procurement stalls | Commission purpose-written DPA for educational use |
| No defined pilot exit criteria | Pilots run indefinitely; no conversion | Signed pilot agreement with success metrics before pilot begins |
| Ignoring ethics review timeline | Pilot delayed 4–12 weeks unexpectedly | Ask at first meeting: does this require ethics approval? Who submits it? |
| Treating procurement as enterprise sales | Decision cycle is 6–18 months, not 30–90 days | Map the full decision chain; engage multiple stakeholders early |

---

## Partnership Models

Universities respond better to partnership framing than vendor-client framing, particularly for novel AI tools.

### Model A: Commercial Pilot Agreement
- **Structure:** University evaluates the tool in one real module with student-facing use
- **Duration:** 6–12 weeks
- **University commitment:** Staff time for evaluation, ethics approval, pilot agreement
- **CR8 commitment:** Platform access, technical support, data analysis
- **Conversion:** Procurement recommendation decision at pilot end
- **Best for:** When you have initial evidence and want to convert to an institutional license

### Model B: Co-Research Partnership *(Recommended for initial approach)*
- **Structure:** Joint research project; faculty PI submits ethics application; CR8 is the intervention; both parties co-design the evaluation study
- **Duration:** 12–24 months
- **Output:** Peer-reviewed paper, EEF-compatible evidence base, shared credibility
- **Funding:** Often eligible for Innovate UK, UKRI, or JISC funding
- **Best for:** Early-stage tools that need an evidence base; opens sector-wide adoption pathway

### Model C: Knowledge Transfer Partnership (KTP)
- **Structure:** Formal UKRI-funded partnership with a university technology transfer office
- **Duration:** 12–24 months
- **Output:** Joint IP on new features; product shaped by pedagogical expertise
- **Funding:** KTP grant covers ~50–67% of costs; both parties co-fund the rest
- **Best for:** When you want co-designed product development and long-term institutional embedding

### Recommended Sequencing
**Co-Research Partnership** (build evidence) → **Commercial Pilot** (prove value, convert) → **Innovation Partnership or Institution-Wide License** (scale)

---

## University-Specific Intelligence

### UK Market Context
- ~140 higher education institutions in the UK
- Target segment: research-intensive universities (Russell Group, Civica Alliance) + teaching-focused post-1992s with strong professional programmes (law, health, engineering)
- Key decision-making bodies: Learning & Teaching Committee, Digital Education Board, IT Governance
- Common LMS: Canvas, Moodle (largest open-source deployment globally), Blackboard (declining)
- Common SIS: SITS/e:Vision (dominant in UK HE)

### Channels for First Contact
1. **Learning Technologist / Director of Digital Education** — most receptive to initial conversation; often has budget and influence
2. **VC Education / Pro-Vice Chancellor (Education)** — strategic buy-in; needed for cross-faculty pilot
3. **EdTech conference circuit:** UCISA, ALT (Association for Learning Technology), HEA (Higher Education Academy) events
4. **JISC** — the UK HE digital agency; their endorsement or partnership is a credibility signal to all UK universities
5. **Innovate UK smart grant** — signals commercial viability and opens university research office doors
