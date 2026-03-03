# Agentic Coding Best Practices: A Practitioner's Guide

**For teams building agentic AI solutions with software-based technology stacks**
**Primary tooling: Claude Code | Secondary: GitHub Copilot**

---

## Context: Agentic Software + Software-Based Tech

This guide addresses a specific class of development: **agentic software combined with software-based technology to deliver agentic AI solutions**. This means your codebase is not just *built by* AI agents — it may also *contain* AI agents as part of the product itself. The development workflow uses Claude Code as the primary agentic coding tool, with GitHub Copilot as a secondary assistant for inline completions and code review.

This dual nature — agents building agent-powered software — creates unique challenges. Your agent memory files (AGENTS.md, CLAUDE.md) must serve both the development workflow and potentially inform the product's own agent architecture. Your context management strategy must account for both the complexity of the agentic product you're building and the context demands of the agent building it.

The practices below are drawn from Anthropic's engineering research, CodeScene's peer-reviewed studies (January 2026), the Linux Foundation AGENTS.md specification, and real-world practitioner reports from teams shipping 20+ agent-authored PRs per day. Every recommendation is grounded in empirical findings, not opinion.

---

## 1. The Agent Memory Layer: AGENTS.md, CLAUDE.md, and Instruction Architecture

The single highest-leverage file in any agentic project is its agent instruction file. This is the project's permanent brain — loaded into every session, shaping every decision the agent makes.

### Three Files, Three Purposes

**AGENTS.md** is the universal, cross-tool standard donated to the Linux Foundation's Agentic AI Foundation in December 2025. Co-founded by OpenAI, Anthropic, and Block, it is supported by 20+ tools including Claude Code, GitHub Copilot, Cursor, Codex, VS Code, Gemini CLI, Windsurf, RooCode, Devin, and Aider. Over 60,000 open-source projects have adopted it. The format is plain Markdown with no required fields, no YAML frontmatter, and no special syntax.

Since you use both Claude Code and GitHub Copilot, AGENTS.md is your cross-tool bridge — it is the one file both tools read natively.

**CLAUDE.md** is Claude Code's tool-specific instruction file with `@import` support (recursive up to 5 levels deep), path-scoped rules via `.claude/rules/`, and tight integration with Claude Code's auto-memory system. The critical caveat: Claude Code wraps CLAUDE.md content in a `<system-reminder>` tag that tells the model to ignore content that isn't relevant to the current task. This means bloated, unfocused files actively degrade performance.

**CLAUDE.local.md** handles personal, machine-specific overrides — sandbox URLs, personal debugging preferences, environment-specific configuration. It is added to `.gitignore` so it never enters version control.

### Your Setup Package in Practice

The starter templates from your setup package demonstrate the correct architecture. Here is how each file maps to the three-tier system:

**Your AGENTS.md template** (universal, cross-tool):
```markdown
# AGENTS.md
<!-- Universal agent memory file. Loaded at the start of every session by
     Claude Code, Cursor, Copilot, Windsurf, Codex, and other compatible tools.
     Keep this file UNDER 100 LINES. -->

## Project Overview
[Project name] — [one sentence description of what it does and the primary tech stack].

## Tech Stack
- Language: [e.g. TypeScript strict mode]
- Framework: [e.g. Next.js 14 App Router]
- Database: [e.g. PostgreSQL via Prisma]
- Testing: [e.g. Vitest + Playwright for E2E]
- Docs: MkDocs (Material theme) — source in `/docs/`

## Build & Test Commands
# Install / Dev server / Run all tests / Lint / Build docs

## Code Standards
- [e.g. Use named exports over default exports]
- [e.g. Prefer positive instructions: describe what TO do, not what NOT to do]

## Testing Requirements
- All new features require tests before marking complete
- Do not mark a task complete until you have seen the test pass with your own tool calls

## Definition of Done
1. Tests pass
2. Linter passes
3. Docs updated if behaviour changed
4. PROGRESS.md updated with what was done
5. E2E smoke test passes (run ./scripts/init.sh to verify)

## Session Start Protocol
1. Read PROGRESS.md for current project state
2. Run ./scripts/init.sh to verify the app is in a working state
3. Fix any broken state BEFORE starting new work

## Key Directories
/docs/          → MkDocs documentation source
/docs/adr/      → Architecture Decision Records
/docs/research/ → Implementation research notes
/.claude/       → Agent memory, skills, slash commands, and subagents
/scripts/       → Automation scripts including init.sh
```

Note: this template stays under 80 lines. It contains only universal rules — things every tool and every session needs. Task-specific guidance lives elsewhere.

**Your CLAUDE.md template** (Claude Code-specific extensions):
```markdown
# CLAUDE.md
@import AGENTS.md

## Claude-Specific Behaviours

### Subagent Routing
- Use the Explore subagent for read-only codebase search
- Use the Plan subagent before implementing anything non-trivial
- Do NOT spawn subagents for simple single-file changes

### Context Management
- When context feels crowded, stop and write a summary to PROGRESS.md before continuing
- Start fresh sessions for new features
- If uncertain about a past decision, check docs/adr/ before guessing

### Hallucination Prevention
- For any external library or API, check docs/research/ first
- If research docs don't cover it, perform a web search for current official docs
- Pin library versions in all research queries
```

This file uses `@import AGENTS.md` to avoid duplication, then adds only Claude Code-specific behaviours that GitHub Copilot would not understand. The `@import` directive is Claude Code-exclusive and cascades recursively up to 5 levels.

**Your CLAUDE.local.md template** (personal, never committed):
```markdown
# CLAUDE.local.md
<!-- Personal overrides for THIS developer's machine. Add to .gitignore. -->

## Local Environment
# Local dev URL: http://localhost:3000
# Database URL: postgresql://localhost:5432/myapp_dev

## Personal Shortcuts
# My preferred test data set: [describe it]
# My local MkDocs preview: http://127.0.0.1:8000
```

### The Instruction Budget Problem

Claude Code's built-in system prompt contains approximately 50 individual instructions consuming ~20K tokens before your CLAUDE.md even loads. Frontier thinking LLMs can reliably follow roughly 150–200 instructions total. This means Claude Code's system prompt already consumes nearly a third of available instruction-following capacity.

Empirical data on adherence:
- Files under 200 lines: **92%+ instruction adherence**
- Files over 400 lines: **71% instruction adherence**
- HumanLayer's production CLAUDE.md: under 60 lines

Your template's approach of keeping AGENTS.md under 100 lines is correct. The `@import` pattern in CLAUDE.md avoids bloating the Claude-specific file while pulling in the universal rules.

### The Negative Instruction Problem

LLMs follow positive instructions more reliably than negative ones. Models perform positive selection (choosing what token comes next), not explicit avoidance. Telling a model "Don't use mock data" forces it to process the concept of mock data, increasing the probability of that behaviour.

Your template already follows this pattern well — note the code standards example: "Prefer positive instructions: describe what TO do, not what NOT to do."

Rewrite every "don't" into a "do":
- "Don't use mock data" → "Use only real-world data from the database"
- "Never create new files for fixes" → "Apply all fixes to existing files"
- "Avoid verbose comments" → "Write concise, professional comments"

### Hierarchical Loading for Monorepos

Claude Code loads instruction files via two mechanisms. **Ancestor loading** walks upward from the current working directory at startup, loading every CLAUDE.md found. **Descendant loading** is lazy — CLAUDE.md files in subdirectories load only when Claude reads files in those directories.

```
project-root/
├── CLAUDE.md                  # Loaded at startup — universal rules
├── AGENTS.md                  # Cross-tool compatibility
├── .claude/
│   └── rules/
│       └── api-standards.md   # Path-scoped YAML frontmatter
├── frontend/
│   └── CLAUDE.md              # Lazy-loaded when working on frontend
├── backend/
│   └── CLAUDE.md              # Lazy-loaded when working on backend
└── shared/
    └── CLAUDE.md              # Lazy-loaded when working on shared code
```

OpenAI's main repository contains 88 AGENTS.md files — one near each significant code boundary. This ensures agents always receive relevant context.

### Symlink Strategy for Claude Code + GitHub Copilot

Since you use both tools, keep AGENTS.md as the single source of truth with symlinks:

```bash
# AGENTS.md as source of truth
ln -sfn AGENTS.md .github/copilot-instructions.md
# CLAUDE.md imports AGENTS.md via @import (no symlink needed)
```

For teams adding Cursor or other tools later, `npx rule-porter --to agents-md` converts between formats.

### Section Checklist

- [ ] Root AGENTS.md under 100 lines with only universal rules
- [ ] CLAUDE.md uses `@import AGENTS.md` and adds only Claude-specific behaviours
- [ ] CLAUDE.local.md in `.gitignore` with personal overrides
- [ ] All negative instructions rewritten as positive directives
- [ ] `.github/copilot-instructions.md` symlinked to AGENTS.md for Copilot
- [ ] Subdirectory instruction files for each major code boundary
- [ ] `.claude/rules/` directory with path-scoped rules using YAML frontmatter
- [ ] Auto-memory reviewed and curated monthly

---

## 2. Project Structure for AI Navigation

Agents do not browse a codebase the way humans do. They must systematically read files, trace imports, and map dependencies — consuming context tokens with every step.

### The Package Explosion Problem

Practitioner testing found agents navigating 15 micro-packages in a monorepo can spend 5+ minutes just mapping dependencies before writing a single line of code. The same functionality in 3 well-structured packages was understood in minutes.

**Prefer flat, colocated structures:**
```
# Preferred: flat, colocated
src/
├── auth/
│   ├── auth.service.ts
│   ├── auth.service.test.ts
│   ├── auth.types.ts
│   └── README.md
├── billing/
│   ├── billing.service.ts
│   ├── billing.service.test.ts
│   └── billing.types.ts
└── CLAUDE.md
```

### Barrel Files Destroy Traceability

Barrel files (`index.ts` re-exports) create indirection that forces agents to trace extra layers. Atlassian reported 75% faster builds after removing them. For agents, every barrel file is a dead end that wastes tokens. Use direct imports: `from './auth/auth.service'` not `from './auth'`.

### Code Health as AI-Readiness Metric

CodeScene's peer-reviewed research (January 2026) provides the strongest empirical evidence: AI-generated code in unhealthy codebases increases defect risk by at least 30%. The study only included code with Code Health scores of 7.0+ — degradation in truly unhealthy code was not even measured.

Target: **Code Health score 9.5+** (on CodeScene's 1–10 scale). Healthy code delivers 2x faster development, 15x fewer defects, and 9x more predictable delivery.

### Your Directory Structure Template

Your setup package defines this key directory layout:
```
/docs/          → MkDocs documentation source
/docs/adr/      → Architecture Decision Records (read before structural decisions)
/docs/research/ → Implementation research notes (read before using external APIs)
/.claude/       → Agent memory, skills, slash commands, and subagents
/scripts/       → Automation scripts including init.sh
```

This structure supports both Claude Code's skill system (`.claude/skills/`) and general-purpose agent navigation. Add README.md files at each significant directory (20–40 lines covering purpose, key files, patterns used).

### Section Checklist

- [ ] Package structure flat enough that agents map dependencies in under 2 minutes
- [ ] Tests, types, and documentation colocated with implementation code
- [ ] No barrel files — all imports use direct paths
- [ ] Code Health score measured and maintained at 9.5+
- [ ] README.md at root and each significant directory
- [ ] CONTRIBUTING.md as single source of truth for coding patterns

---

## 3. Context Management: The Central Constraint

Anthropic's official documentation states it directly: "Most best practices are based on one constraint: Claude's context window fills up fast, and performance degrades as it fills."

### Within-Session Context Rot

Claude Code's standard context window is 200K tokens, with ~20K consumed by system prompt and tools before your conversation begins. Auto-compaction triggers at approximately 83.5% utilisation.

Performance degradation is non-linear:
- At 70% utilisation: precision begins degrading
- At 80–100%: degradation accelerates sharply
- Opus 4.6 suffers a 17-point accuracy drop using the full 1M window (93% → 76%)

**The 30-minute sprint cadence**: Sessions under 80K tokens stay below compaction. 2-hour sessions hit 2–3 compactions with progressive quality dilution.

Key commands:
- `/context` — reveals current token breakdown
- `/clear` — wipes conversation history (use after every commit)
- `/compact` — summarises and replaces history (use at natural breakpoints)
- `/compact focus on the API changes` — directed compaction preserving specific context

### Cross-Session Amnesia: The PROGRESS.md Pattern

Every new session starts with a blank context window. Your setup package's PROGRESS.md template solves this:

```markdown
# PROGRESS.md
## Current Status
**Last updated:** [DATE]
**Overall project phase:** [e.g. MVP development / Beta / Production maintenance]

## What's Working
- [ ] Add completed features here

## In Progress
- [ ] [Feature name] — [what has been done, what's left, which files are involved]

## Known Broken / Blocked
- [ ] None

## Next Steps (Prioritised)
1. [First task]
2. [Second task]

## Recent Decisions
| Date | Decision | Rationale | ADR |
|------|----------|-----------|-----|
```

Anthropic's engineering research recommends JSON over Markdown for structured state — agents are "less likely to inappropriately change or overwrite JSON files." For feature lists and task tracking, use `feature_list.json`. Keep PROGRESS.md for narrative state.

### The Initialiser + Coding Agent Pattern

From Anthropic's long-running agent research:

1. **Initialiser agent** runs once: creates `init.sh`, `feature_list.json`, `claude-progress.txt`, makes initial commit
2. **Each coding session**: reads git log + progress → picks one feature → implements → tests end-to-end → commits → updates progress

Your `init.sh` template implements step 2's session verification:

```bash
#!/usr/bin/env bash
set -e
echo "▶ Checking dependencies..."
echo "▶ Running linter..."
echo "▶ Running unit tests..."
echo "▶ Checking build..."
echo "▶ Starting dev server for smoke test..."
echo "✅ All checks passed — safe to proceed"
echo "  Read PROGRESS.md for current task state"
```

Configure this with your actual build/test/lint commands. The agent should fix any failures before starting new work.

### Subagents as Context Isolation

Each subagent operates in its own isolated 200K-token window, receiving ~500 tokens of task context. When complete, it returns only a summary (~1–2K tokens) to the main conversation. Up to 10 subagents can run simultaneously.

Your CLAUDE.md template correctly routes subagents:
```markdown
- Use the Explore subagent for read-only codebase search
- Use the Plan subagent before implementing anything non-trivial
- Do NOT spawn subagents for simple single-file changes
```

Custom subagents are defined in `.claude/agents/`:
```markdown
---
name: code-reviewer
description: Expert code reviewer. Use proactively after code changes.
tools: Read, Grep, Glob, Bash
model: sonnet
---
You are a senior code reviewer. Check for:
1. Logic errors and edge cases
2. Security vulnerabilities
3. Performance regressions
4. Consistency with existing patterns
```

Anthropic's multi-agent system (Opus lead + Sonnet subagents) outperformed single-agent Opus by 90.2%.

### Section Checklist

- [ ] `/clear` used after every commit and task switch
- [ ] PROGRESS.md maintained as cross-session state artifact
- [ ] Feature/task state stored in JSON format
- [ ] Custom subagents defined in `.claude/agents/` for recurring tasks
- [ ] Context never exceeds 85% utilisation during development
- [ ] `init.sh` configured with real build/test/lint commands
- [ ] Git commit messages descriptive enough to serve as session history

---

## 4. Hallucination Prevention and Verification

The most dangerous failure mode is confidently wrong code that appears complete. Agents will declare victory without testing, hallucinate API endpoints, import packages that were never published, and generate plausible code that fails silently.

### Package Hallucination Rates

USENIX Security 2025 study of 576K samples:
- Python: **5.2%** hallucination rate
- JavaScript: **21.7%** hallucination rate
- Prompts for "2025 libraries": hallucinations in **84%** of tasks

### The "Mark as Complete" Failure Mode

Agents routinely declare features "done" without verifying them. Your setup package addresses this with the Definition of Done in AGENTS.md:

```markdown
## Definition of Done
A task is only complete when ALL of the following are true:
1. Tests pass
2. Linter passes
3. Docs updated if behaviour changed
4. PROGRESS.md updated with what was done
5. E2E smoke test passes (run ./scripts/init.sh to verify)
```

And the testing protocol in CLAUDE.md:
```markdown
- Always use tool calls to verify your work — read test output, don't assume it passes
```

One team reduced invalid completions from 80% → 0% by making agents propose intents, then running automated verification before accepting completion.

### Hooks as Structural Guardrails

Claude Code's hooks system enforces verification automatically:

**Stop hooks** — run type checker, linter, tests before allowing completion:
```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{ "type": "command", "command": "pnpm test && pnpm lint" }]
    }]
  }
}
```

**PreToolUse hooks** — block dangerous operations before they execute.

**PostToolUse hooks** — run formatters after every file write:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write(*.ts)",
      "hooks": [{ "type": "command", "command": "npx biome format --write $file" }]
    }]
  }
}
```

### Language Selection for Reduced Hallucination

**Go**: Recommended for backend — compiled language catches hallucinations at compile time, fast test caching, uniform style produces valid code 95% first-shot.

**TypeScript (strict mode)**: Recommended for frontend — strong type system catches hallucinations quickly. Enable `strict: true`, `noImplicitAny: true`, `strictNullChecks: true`.

**Python**: 5.2% hallucination rate but agents struggle with pytest fixtures, async event loops, and slow interpreter boot.

**JavaScript npm ecosystem**: 21.7% hallucination rate. Avoid for agentic workflows where possible.

### Your Research Template Prevents Hallucination

Your `RESEARCH-TEMPLATE.md` is specifically designed to prevent hallucination during implementation:

```markdown
# Research: [Topic / Library / API Name]
**Library version:** [exact version, e.g. stripe@14.2.0]
**Status:** [Current | Needs update | Superseded]

## Sources Consulted
| Source | URL | Date accessed |
Official docs, Changelog, GitHub issues

## What We Found
### The Correct Approach
[Working code example with exact library version]

## What We Ruled Out (and Why)
| Approach | Why Rejected |

## Known Gotchas / Edge Cases
```

The key fields are **Library version** (prevents wrong-version code generation) and **What We Ruled Out** (prevents the agent from rediscovering rejected approaches). The instruction in your CLAUDE.md ties it together:

> "For any external library or API, check `docs/research/` first. If research docs don't cover it, perform a web search for the current official docs before writing implementation code."

### Section Checklist

- [ ] Testing tools installed (runners, Playwright/Puppeteer MCP, curl)
- [ ] API documentation injected for all external services
- [ ] Feature status derived from test results, not agent self-reporting
- [ ] Stop hooks enforce test/lint pass before task completion
- [ ] PostToolUse hooks run formatters on every write
- [ ] Research template used for every new external library/API
- [ ] Library versions pinned in project configuration and CLAUDE.md

---

## 5. Skills: Modular, On-Demand Agent Knowledge

Skills solve the fundamental tension between giving agents enough knowledge and not overwhelming their context window. Published as an open standard in October 2025, they follow a progressive disclosure model.

### How Skills Work

**Level 1 — Metadata only**: At startup, Claude loads only the `name` and `description` from every installed Skill's YAML frontmatter. Cost: ~100 tokens per Skill.

**Level 2 — SKILL.md body**: Loaded when Claude determines the Skill is relevant. Target: under 500 lines.

**Level 3+ — Supporting files**: Scripts, templates, references load on-demand. Scripts execute externally — their code never enters the context window.

### Your Session Handoff Skill

Your setup package includes a production-ready Skill example:

```yaml
---
name: session-handoff
description: Use at the END of a working session to write a structured handoff
  document, or at the START of a session to read and orient from the previous
  session's state. Triggers on phrases like "wrap up", "end of session",
  "save progress", "what's the current state", "orient yourself".
---
```

This Skill demonstrates best practices:
- **Specific trigger keywords**: "wrap up", "end of session", "save progress"
- **Clear bidirectional purpose**: both writing and reading handoffs
- **Concrete rules**: "NEVER mark a feature complete in PROGRESS.md without having seen a test pass via tool call"

### The Description Field Is Everything

The description triggers Skill loading — it is the primary activation mechanism. A vague description like "handles deployment" activates less reliably than:

```yaml
description: >
  Deploy the application to staging environment. Use when the user asks to
  deploy, push to staging, or test in a staging environment. Handles Docker
  build, ECR push, ECS service update, and health check verification.
```

Include trigger contexts, relevant file types, task types, and keywords the user might use.

### Skill Architecture

```
.claude/skills/
├── deploy-staging/
│   ├── SKILL.md              # Instructions + YAML frontmatter
│   ├── scripts/
│   │   └── deploy.sh         # Executed externally, not loaded
│   ├── references/
│   │   └── aws-config.md     # Loaded on-demand
│   └── examples/
│       └── deploy-output.md  # Successful deployment example
├── session-handoff/
│   └── SKILL.md              # Your template
├── api-endpoint/
│   ├── SKILL.md
│   └── references/
│       └── openapi-spec.yaml
```

### When to Create a Skill vs Other Constructs

| Construct | Use When |
|-----------|----------|
| **Skill** | Repeatable task needing supporting files; loads on-demand |
| **Path-scoped rule** (`.claude/rules/`) | Universal instruction for specific file patterns; under 50 lines |
| **CLAUDE.md** | Universal constraint; under 5 lines; applies every session |
| **Subagent** (`.claude/agents/`) | Specialised role with isolated context |
| **Slash command** | Single-step convenience shortcut |

### Development Workflow

1. Run agents on representative tasks, observe failures
2. Build a Skill addressing the gap
3. Have a **fresh Claude session** (Claude B) test the Skill — the author (Claude A) is biased
4. Iterate: remove explanations the model already knows, split when SKILL.md exceeds 500 lines

### Section Checklist

- [ ] Skills directory at `.claude/skills/` with clear naming
- [ ] Each Skill has keyword-rich description in YAML frontmatter
- [ ] SKILL.md bodies under 500 lines
- [ ] Scripts in `scripts/` for external execution
- [ ] Skills tested with a fresh Claude session
- [ ] No duplication between Skills and CLAUDE.md
- [ ] Skills reviewed quarterly

---

## 6. Documentation Architecture for Dual-Audience Consumption

Documentation in agentic projects serves two audiences: humans who skim and infer, and agents who depend on explicit structure and machine-readable signals.

### The llms.txt Standard

Proposed September 2024, adopted by 600+ sites. A `/llms.txt` Markdown file at the documentation root containing the project name, a summary, and organised links. A companion `llms-full.txt` concatenates all docs for full-context consumption. Reduces token consumption 90%+ vs HTML parsing.

For MkDocs, `mkdocs-llmstxt` auto-generates these files. `mkdocs-mcp` bridges docs to AI via Model Context Protocol.

### Architecture Decision Records

Your ADR template captures the "why" that agents need:

```markdown
# ADR-[NNN]: [Title]
## Status: [Proposed | Accepted | Deprecated | Superseded]
## Context: [What is the issue that we're seeing that motivates this decision?]
## Decision: [What is the change that we're proposing/have agreed to?]
## Consequences: [What becomes easier or harder because of this change?]
```

Store in `docs/adr/` with sequential numbering. Add this instruction to CLAUDE.md:

```markdown
When making architectural decisions (new dependencies, design patterns,
data model changes), create an ADR in docs/adr/ following the template.
```

Without ADRs, agents will "improve" code by reversing deliberate architectural choices.

### Section Checklist

- [ ] llms.txt file at documentation root
- [ ] ADR directory with sequential numbering and template
- [ ] CLAUDE.md instruction to create ADRs for architectural decisions
- [ ] MkDocs MCP or search server configured for agent docs access
- [ ] READMEs at every significant directory level
- [ ] Business rules and external constraints explicitly documented

---

## 7. Specification-Driven Development

The gap between a project manager's task description and code an agent can ship is where most agentic workflows break down. Specifications are not documentation — they are implementation contracts.

### The 50-Minute Horizon

METR research (March 2025): frontier models have 50% success at 50-minute tasks. Approaches 100% for <4-minute tasks, drops below 10% for >4-hour tasks. Horizon doubles every 7 months.

**Implication**: Decompose every feature into tasks achievable within 30–50 minutes of agent work. Your AGENTS.md's Definition of Done enforces this at the task level.

### GitHub Issues as Agent Task Units

Structure Issues with everything an agent needs:

```markdown
## Feature: Rate limiting for API endpoints

### Acceptance Criteria
- [ ] Rate limit: 100 requests per minute per API key
- [ ] Rate limit headers in all responses
- [ ] 429 response with Retry-After header when exceeded
- [ ] Rate limit state stored in Redis
- [ ] Integration tests covering normal flow, limit hit, and reset

### Files Likely Modified
- src/middleware/rate-limiter.ts (new)
- src/api/router.ts (apply middleware)
- tests/integration/rate-limiting.test.ts (new)

### Out of Scope
- Do NOT modify authentication middleware
- Do NOT change existing API response formats
```

### Two-Tier Agent Architecture

For complex features: **Planner agent** (Opus, read-only) decomposes work → **Implementer agent** (Sonnet, full access) executes one task at a time.

The `opusplan` alias — Opus for planning, auto-switch to Sonnet for execution — delivers 80–90% cost savings vs all-Opus.

### Plan Mode Before Implementation

Claude Code's Plan Mode (Shift+Tab) restricts to read-only operations. Planning (5–9 minutes) followed by implementation (18–35 minutes) produces faster total completion than jumping to coding.

**Rule of thumb**: Enter plan mode for any task with 3+ steps, multi-file changes, or architectural decisions.

### Section Checklist

- [ ] Specifications with measurable acceptance criteria before work begins
- [ ] Tasks decomposed into 30–50 minute agent work units
- [ ] Issues structured with acceptance criteria, files, and scope
- [ ] Plan mode used before non-trivial implementation
- [ ] Definition of Done enforced for every agent task
- [ ] Feature flags used for incremental delivery
- [ ] Orchestrator + specialist pattern for multi-concern features

---

## 8. Research Before Implementation, Never During

Agents that research while implementing produce the worst outcomes. The pattern that works: **research first, document findings, clear context, implement from the research artifact**.

### The Retrieval-Augmented Implementation Pattern

1. Create a research subagent with read-only tools (Glob, Grep, Read, WebSearch)
2. Subagent explores codebase, checks versions, reads docs
3. Produces a structured findings document using your RESEARCH-TEMPLATE.md
4. Clear context
5. Implementation agent reads only the findings document

Your template's structure is precisely designed for this workflow:

```markdown
## Question Being Answered
> How do we [do X] using [library Y] in the context of [our project]?

## Sources Consulted
| Source | URL | Date accessed |

## The Correct Approach
[Working code example with exact version]

## What We Ruled Out (and Why)
| Approach | Why Rejected |

## Files This Affects
- [file path] — [how it's affected]
```

The "Files This Affects" section is particularly valuable — it gives the implementation agent an immediate scope boundary.

### Token Consumption

Analysis of 7 coding agents: Claude Code uses 108–117K tokens for iterative lexical search. Aider's tree-sitter AST with PageRank uses only 8.5–13K tokens. Pre-research dramatically reduces implementation-phase token burn.

### Version Pinning

Include versions in both CLAUDE.md and research docs: "React 18 with TypeScript, Vite, Tailwind" prevents wrong-version code generation. Your research template's **Library version** field enforces this.

### Section Checklist

- [ ] Research subagent created for every non-trivial task
- [ ] Findings documented using RESEARCH-TEMPLATE.md before implementation
- [ ] Context cleared between research and implementation
- [ ] Third-party API versions verified before integration code
- [ ] Library versions pinned in project configuration
- [ ] `docs/research/INDEX.md` maintained as knowledge base index
- [ ] "What changed" research run before dependency upgrades

---

## 9. Observability and Debugging Agent Behaviour

Agent behaviour is opaque by default. Without observability, debugging failures becomes guesswork.

### Logging Proxy

The `ANTHROPIC_BASE_URL` proxy pattern routes all Claude Code API calls through a logging proxy:

```bash
ANTHROPIC_BASE_URL=http://localhost:8000/ claude
```

This captures prompts, responses, tool calls, and token counts — complete visibility without modifying agent code.

**claude-code-logger** provides chat mode visualisation, verbose mode, and file logging. **claude-code-transcripts** converts session transcripts to detailed HTML for post-hoc analysis.

### Hook-Based Tracing

PreToolUse hooks can log every tool call:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "",
      "hooks": [{ "type": "command", "command": "echo \"$(date) $TOOL_NAME\" >> .claude/agent-trace.log" }]
    }]
  }
}
```

### Platforms

**Langfuse** (open-source): traces decision workflows with OpenTelemetry support. **Braintrust**: gateway-based proxy with no code changes. **Arize/Phoenix**: structured tracing with duration, token usage, cost per step.

### Section Checklist

- [ ] Logging proxy or transcript tool capturing agent sessions
- [ ] Hook-based tracing for tool call audit trail
- [ ] Token consumption tracked per session type
- [ ] Quiet failure detection (infinite loops, context abandonment)

---

## 10. Code Review for Agent-Generated Code

An industry analysis of 470 PRs found AI-generated code contained 1.7x more defects than human code. 45% of AI-generated code contains security flaws. Only 48% of developers consistently review AI-assisted code before committing.

### Cross-Model Review

Your dual-tool setup (Claude Code + GitHub Copilot) naturally enables cross-model review. Generate with Claude Code, review with Copilot's inline suggestions — each has distinct blind spots.

For formal review: Claude Code's GitHub Actions integration (`anthropics/claude-code-action@beta`) enables automated PR review triggered on every push.

### Automated Enforcement

PostToolUse hooks for formatters (as shown in Section 4). Stop hooks ensure the agent cannot declare completion until checks pass. Pre-commit hooks run formatters, linters, type checkers, and security scanners.

Use CLAUDE.md for semantic rules (architecture, patterns); use hooks for mechanical rules (formatting, imports).

### Section Checklist

- [ ] All agent PRs reviewed with same rigour as human code
- [ ] Cross-model review configured (Claude Code generates, Copilot reviews or vice versa)
- [ ] PostToolUse hooks for formatters
- [ ] CI pipeline includes security scanning (SAST/DAST)
- [ ] Agent PR review bot installed

---

## 11. Cost and Efficiency Management

An unconstrained agent can consume $5–8 per task. Research loops running 10 cycles can burn 50x the tokens of a single linear pass. Output tokens cost ~4x more than input tokens.

### Model Routing

| Model Class | Cost | Use For |
|-------------|------|---------|
| **Haiku 4.5** | 1x | Exploration, file search, summarisation, status checks |
| **Sonnet** | 12x | Standard code generation, test writing, documentation (90% of work) |
| **Opus** | 60x | Architecture, complex debugging, multi-step reasoning |

The `opusplan` alias: Opus for planning, auto-switch to Sonnet for execution — 80–90% savings vs all-Opus.

### Token Optimisation

- **Prompt caching**: saves 50–90% on repeated prompt tokens
- **History pruning** via `/compact`: cuts per-conversation tokens 70–90%
- **Reference files instead of pasting**: 500-line paste = ~4K tokens
- **Progressive disclosure via Skills**: only load knowledge when needed
- **Batch API**: 50% discount for 24-hour turnaround (background tasks)

### Section Checklist

- [ ] Model routing configured by task type
- [ ] Prompt caching enabled for repeated context
- [ ] Skills used for progressive knowledge disclosure
- [ ] Token budget tracked per session type
- [ ] Batch API used for non-urgent tasks

---

## 12. Security Guardrails

ProjectDiscovery generated 3 full-stack applications (~30,000 lines) using Codex, Cursor, and Claude Code without prompting for security. Result: 70 exploitable vulnerabilities including 18 Critical/High issues. Prompt injection attacks achieve up to 84% success rates.

### Sandbox Architecture

Claude Code uses OS-level primitives:
- **Linux**: Bubblewrap (Landlock + Seccomp profiles)
- **macOS**: Seatbelt (`sandbox_init`)

Non-negotiable controls: network egress controls, file write restrictions outside workspace, secret isolation, lifecycle management.

### Permission Tiers

| Tier | Actions |
|------|---------|
| ✅ **Always** | Read files, run tests, format, search, grep |
| ⚠️ **Ask first** | Schema changes, add dependencies, modify CI |
| 🚫 **Never** | Commit secrets, push to main, modify production, access node_modules internals |

### Version Control for Everything

All agent configs (AGENTS.md, CLAUDE.md, Skills, hooks) must be version-controlled alongside code. Changes to CLAUDE.md should go through the same PR review as application code. Your setup package's README correctly notes which files to commit and which to gitignore (CLAUDE.local.md).

### Section Checklist

- [ ] Agent sandbox with network egress controls and file restrictions
- [ ] No agent write access to production
- [ ] Risk-tiered approval process defined
- [ ] All prompts, Skills, CLAUDE.md version-controlled and PR-reviewed
- [ ] Secrets isolated from agent environment
- [ ] Package names verified against registry before installation
- [ ] SAST/DAST scanning in CI

---

## 13. Testing Strategy: The Ground Truth

In agent-driven development, tests *define* code. They are the specification, the acceptance criteria, the objective measure of "done" that agents otherwise lack.

### Tests as Specification

Write comprehensive failing tests from a specification, then instruct the agent to make them pass. This provides "user-defined, context-specific guard rails" that channel the agent toward correct behaviour.

Your AGENTS.md template enforces this:
```markdown
## Testing Requirements
- All new features require tests before marking complete
- Do not mark a task complete until you have seen the test pass with your own tool calls
```

### The Broken Foundation Problem

Your `init.sh` script is the first line of defence. Before any agent begins new work, it verifies the existing system works. Your template runs dependency checks, linting, unit tests, build checks, and a dev server smoke test.

**Critical**: configure `init.sh` with your actual commands (the template ships with placeholders). An `init.sh` that only echoes "OK" provides zero protection.

### Testing Pyramid for Agents

**Unit tests**: Run continuously during sessions. Fast feedback (<5s). Many of these.
**Integration tests**: Run after each commit. Stable interfaces. Some of these.
**E2E tests**: Run in CI before merge. Critical workflows. Few but essential.

E2E tests are 3–5x more expensive to maintain but resilient to refactoring — agents are remarkably good at writing code that passes unit tests while failing in integration.

### Section Checklist

- [ ] Failing tests written from specifications before implementation
- [ ] Existing test suite passes before any new agent task starts
- [ ] Unit tests run continuously during sessions (<5s feedback)
- [ ] E2E tests run in CI before merge
- [ ] Coverage gates prevent reduction on PRs
- [ ] Browser automation available for UI verification
- [ ] `init.sh` configured with real commands (not placeholders)

---

## Session Workflow: Putting It All Together

Your setup package's README defines the complete workflow:

**Start every session:**
> Read PROGRESS.md, then run ./scripts/init.sh and report any failures.

**Before implementing with external libraries:**
> Check docs/research/ for existing notes, or create a new research note using RESEARCH-TEMPLATE.md before writing any code.

**Before architectural decisions:**
> Check docs/adr/ for relevant prior decisions.

**End every session:**
> Use the session-handoff skill to update PROGRESS.md.

This workflow ensures every session starts informed, implements safely, and leaves state for the next session.

---

## Master Checklist

### Agent Instruction Files
- [ ] Root AGENTS.md under 100 lines, universal rules only
- [ ] CLAUDE.md uses `@import AGENTS.md`, adds only Claude-specific behaviours
- [ ] CLAUDE.local.md in `.gitignore`
- [ ] `.github/copilot-instructions.md` symlinked to AGENTS.md
- [ ] All negative instructions rewritten as positive directives
- [ ] Subdirectory instruction files at each code boundary
- [ ] `.claude/rules/` with path-scoped rules
- [ ] Auto-memory reviewed monthly

### Project Structure
- [ ] Flat package structure navigable in under 2 minutes
- [ ] Tests, types, docs colocated with implementation
- [ ] No barrel files — direct import paths
- [ ] Code Health at 9.5+
- [ ] README.md at root and significant directories
- [ ] CONTRIBUTING.md as pattern source of truth

### Context Management
- [ ] `/clear` after every commit and task switch
- [ ] PROGRESS.md maintained across sessions
- [ ] Feature/task state in JSON
- [ ] Custom subagents in `.claude/agents/`
- [ ] Context never exceeds 85% utilisation
- [ ] `init.sh` configured with real commands

### Verification and Testing
- [ ] Testing tools installed (runners, browser automation, HTTP clients)
- [ ] API documentation injected for integrations
- [ ] Feature status from test results, not self-reporting
- [ ] Stop hooks enforce test/lint pass
- [ ] Failing tests before implementation
- [ ] E2E tests in CI before merge
- [ ] Pre-flight smoke test every session

### Skills and Documentation
- [ ] Skills directory with keyword-rich descriptions
- [ ] SKILL.md bodies under 500 lines
- [ ] llms.txt at documentation root
- [ ] ADR directory with template
- [ ] Research findings in `docs/research/` with index
- [ ] Session-handoff skill installed and tested

### Workflow and Project Management
- [ ] Specifications with measurable acceptance criteria
- [ ] Tasks decomposed into 30–50 minute units
- [ ] Issues with acceptance criteria, files, and scope
- [ ] Plan mode before non-trivial tasks
- [ ] Definition of Done defined and enforced
- [ ] Research template used before implementation

### Security and Operations
- [ ] Agent sandbox with egress controls
- [ ] No agent access to production
- [ ] Risk-tiered approval process
- [ ] All configs version-controlled and PR-reviewed
- [ ] PostToolUse hooks for formatters
- [ ] Cross-model review (Claude Code + Copilot)
- [ ] Observability proxy capturing sessions
- [ ] SAST/DAST in CI
- [ ] Package names verified against registry

---

## Sources

- Anthropic Engineering: Effective Harnesses, Context Engineering, Multi-Agent Systems (2025–2026)
- CodeScene: "Agentic AI Coding: Best Practice Patterns for Speed with Quality" (January 2026, peer-reviewed)
- Linux Foundation AAIF: AGENTS.md Specification (December 2025)
- HumanLayer: "CLAUDE.md Best Practices" (2025)
- METR Research: "50-Minute Task Horizon" (March 2025)
- USENIX Security 2025: "Package Hallucination Study" (576K samples)
- GitHub: Spec Kit and Agentic Workflows (February 2026)
- Armin Ronacher: "Go for Agentic Backend Development" (2025)
- Simon Willison: Skills Architecture, Hallucination Mitigation (2025)
- SFEIR Institute: Context Management Research (2025)
- NVIDIA AI Red Team: Sandbox Security Requirements (2025)
