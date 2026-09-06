# The Ideal Agentic Project — Structure & Implementation Guide

A reference for standing up a new Claude Code / Claude Agent project that is token-efficient, test-gated, and compounding. It fuses (a) current Anthropic guidance re-verified June 2026, (b) the proven patterns already in your `prototype-harness`, and (c) the user-scope (`~/.claude/`) stack documented in `CLAUDE_SETUP.md`. Companion to `TOKEN-OPTIMIZATION-REVIEW.md`.

---

## 0. Five principles everything else serves

1. **Lean beats complete.** Files under ~200 lines get ~92% instruction adherence; over ~400 lines it drops to ~71%. Every always-on token is paid on every turn. Find the smallest set of high-signal tokens.
2. **The agent never grades its own work — tests do.** Generators confidently praise mediocre output. The grader is the test suite, witnessed via tool calls, never self-reported.
3. **Each unit of work makes the next easier.** Compounding: fix → note → rule → skill → registry component. Artifacts persist context across `/clear`.
4. **Spend top-model tokens on judgment, not typing.** Route by task: cheap models draft and do mechanical work; expensive models critique and decide.
5. **Re-audit the harness every model release.** Newer models need less scaffolding. The simplest thing that works wins; delete rules the model now handles natively.

---

## 1. Canonical directory layout

Three scopes interlock: **project** (git-shared, team-wide), **user** (`~/.claude/`, personal, all projects), and **local** (`*.local.json`, machine-only, never committed). Managed/org policy overrides all.

```
project-root/
├── CLAUDE.md                 # <60 lines; @imports AGENTS.md. Loads every session.
├── AGENTS.md                 # <100 lines; cross-tool standard (Cursor/Copilot/Codex read it too)
├── PROGRESS.md               # tier declaration + tactical state (done/next/blocked)
├── DOMAIN.md                 # DDD-lite: ubiquitous language, entities, events, core domain
├── SPEC.md                   # BDD Given/When/Then guardrail contract
├── .mcp.json                 # project-scope MCP servers (git-shared, prompts teammates to approve)
├── docs/
│   ├── LEARNINGS.md          # append-only compounding log (written by /compound)
│   └── decisions/            # mini-ADRs only for expensive-to-reverse choices
├── fixtures/                 # realistic seed data + typed loader (index.ts)
└── .claude/                  # everything here is version-controlled
    ├── settings.json         # permissions + hooks (team policy)
    ├── settings.local.json   # machine overrides — NOT committed
    ├── rules/
    │   └── design-system.md  # path-scoped (frontmatter paths:) — loads only when src/** touched
    ├── agents/               # subagents: planner, code-reviewer, ui-debugger, …
    └── skills/               # skills = slash commands: <name>/SKILL.md + optional scripts/

~/.claude/                    # USER SCOPE — shared across all your projects
├── CLAUDE.md                 # personal global workflow rules
├── settings.json             # global permissions + global MCP servers
├── skills/                   # personal skills (your whole proto-* pipeline lives well here)
├── agents/                   # personal subagent library (draft/critique pairs, reviewers)
└── projects/<proj>/memory/MEMORY.md   # auto memory (first ~200 lines auto-loaded)
```

**Where your `~/.claude/` stack fits (from CLAUDE_SETUP.md).** Your global layer carries the reusable engine — the full skill set (`/proto-build` and its steps, `/design-dna`, `/compound`, …), the subagent library (draft/critique pairs, reviewers, debuggers), global MCP servers (context7, tavily, playwright, chrome-devtools, cloudflare), and the model-tier policy. A new project then only needs the thin project layer: `CLAUDE.md`, `AGENTS.md`, `.mcp.json`, `design-system.md`, and the per-project artifacts. **Rule of thumb: anything reused across projects belongs in `~/.claude/`; anything specific to one codebase belongs in the project.** Keep user-scope MCP servers to 1–2 — every connected server's tool schemas are loaded into context and are the single largest source of bloat.

---

## 2. Instruction files: CLAUDE.md vs AGENTS.md

| | CLAUDE.md | AGENTS.md |
|---|---|---|
| Read by | Claude Code natively | Open standard (Cursor, Copilot, Codex, Windsurf) |
| Superpowers | `@import`, path-scoped rules, hierarchical memory, survives `/compact` | Portable, tool-agnostic |
| Best practice | Keep thin; `@import ./AGENTS.md` | Put durable project facts here |

**Recommended split** (matches your harness):

- **AGENTS.md (<100 lines)** — the durable, portable facts: project one-liner, stack with **pinned versions**, commands (dev/build/lint/test), Definition of Done per tier, code standards. Write rules in **positive form** ("use real seed data from `fixtures/`", not "don't mock"). One line up top sets response style: *"Output dense, direct text. Omit pleasantries."*
- **CLAUDE.md (<60 lines)** — Claude-Code-specific orchestration: `@AGENTS.md` import, subagent routing (which agent for which trigger), workflow rules, context hygiene (`/clear` after each feature), and the compounding trigger ("same mistake twice → add a one-line rule").

`@import` loads the imported file in full at launch — it improves organization but does **not** reduce token cost. Use it to keep each file readable, not to hide bloat. Only the root `CLAUDE.md` survives `/compact`; nested/subdir `CLAUDE.md` reload on demand.

**Token note:** your current `CLAUDE.md`+`AGENTS.md` baseline is ~864 tokens/turn — already lean. Resist pasting large rule blocks; a 4–5 line "Output Discipline" block captures the verified high-leverage output rules at ~90 tokens vs ~600 for the full dump. (See `TOKEN-OPTIMIZATION-REVIEW.md`.)

---

## 3. The artifact memory layer (compounding)

A small set of files is the project's durable memory; they survive `/clear`, guardrail each downstream step, and stay stable so the API prompt-caches them (they're read by nearly every agent — don't reformat mid-session).

| File | Written by | Role |
|---|---|---|
| `TASK.md` | task-brief | product context extracted from a one-liner/screenshot |
| `EVENT_STORM.md` | event-stormer | domain event timeline, aggregates, hotspots |
| `DOMAIN.md` | domain-model | **source of truth**: ubiquitous language, entities, events, core domain |
| `SPEC.md` | proto-spec | BDD Given/When/Then contract; scenarios become tests verbatim |
| `PROGRESS.md` | session-handoff | tier + done/next/blocked |
| `LEARNINGS.md` | compound | promoted lessons + reuse candidates |
| `design-system.md` | design-dna | exact tokens, fonts, banned patterns, D3 palette |
| `fixtures/` | seed-data | realistic domain data |

The chain — DOMAIN.md stops the agent building the *wrong* thing, SPEC.md stops it building *extra* things, tests stop it *pretending* things work — and each artifact compacts context for the next step. The **ubiquitous language** flows verbatim from DOMAIN.md into spec scenarios, test names, domain code, and UI labels; a renamed concept is a bug.

---

## 4. Skills vs subagents vs slash commands vs rules — decision framework

| Use | When | Loads into context | Invocation |
|---|---|---|---|
| **CLAUDE.md / AGENTS.md** | always-on project knowledge | every turn (keep tiny) | automatic |
| **Rule** (`.claude/rules/*`, path-scoped) | knowledge needed only when certain files are touched | only when `paths:` match | automatic |
| **Skill** (`SKILL.md`) | a reusable workflow/verb; on-demand knowledge | **description always-on (~30–100 tok); body only on trigger** | `/name` or model auto-invokes |
| **Subagent** (`agents/*.md`) | isolated complex subtask (research, review, audit) that would bloat the main thread | runs in **separate context**; returns only a summary | `/name`, routed, or `Agent` tool |
| **MCP server** (`.mcp.json`) | external tool/integration | tool schemas always-on (biggest bloat) | tool calls |

**Decision tree:** always-on knowledge → CLAUDE.md. Needed only for certain paths → rule. Autonomous reusable workflow → skill (description in frontmatter). User-timed action (deploy/commit/send) → skill with `disable-model-invocation: true`. Context-heavy subtask you want isolated → subagent. External system → MCP.

**Skill anatomy & progressive disclosure** — the property that makes 14 skills cost ~500 tokens at startup instead of 70k:

```
.claude/skills/<name>/
├── SKILL.md          # frontmatter (name, description, optional model/allowed-tools) + body <500 lines
├── scripts/          # executable logic — runs externally, never loaded into context
└── templates/        # reference files — loaded only if the body points to them
```

Spend tokens on a **keyword-rich `description`** (it determines trigger accuracy and is always loaded — this is the right place to spend). Keep the body lean; push deterministic logic into `scripts/`. Your skill descriptions (e.g. component-scout listing "check the registry, scout components") are already well-tuned — don't trim them to save tokens; a misfire costs far more than the ~200 tokens saved.

---

## 5. Subagents — design patterns

**Frontmatter schema:**
```yaml
---
name: code-reviewer
description: Reviews changed code; returns SHIP/ITERATE/BLOCK with tool-verified evidence.  # triggers auto-routing
model: sonnet            # alias (opus|sonnet|haiku|fable) or full ID; defaults to parent
tools: Read, Grep, Glob, Bash   # restrict — omit to inherit all
---
System prompt: role, protocol, output contract.
```

Three proven patterns from your stack:

1. **Grader ≠ worker.** planner (read-only decomposition), code-reviewer (SHIP/ITERATE/BLOCK on real tool output), ui-debugger (diagnose browser failures). None of them implement — they plan, verify, or diagnose. This keeps review context out of the builder's window.
2. **Draft → critique.** A Sonnet drafter writes the artifact (domain-modeler, spec-writer, design-director); an Opus critic audits and patches it (opus-domain-critic, opus-spec-critic, opus-design-critic). You keep Opus judgment at the quality-critical points while paying Sonnet rates for the bulk output.
3. **Context isolation = token savings.** A subagent can burn 10k–50k tokens exploring and return a 1k–2k token summary; the main thread never sees the noise. Use subagents for research, review, and audits — Anthropic-measured ~40% context savings vs doing the same work inline.

Restrict `tools:` per role (a reviewer needs Read/Grep/Bash, not Edit) and route the model to the task's difficulty.

---

## 6. Model routing economics

Verified pattern, matching your `CLAUDE_SETUP.md` tier policy. Current model IDs: `claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`, plus the `fable` alias.

| Tier | Model | Use for |
|---|---|---|
| **Judge / decide** | Opus 4.8 | code review, security audit, domain/spec/design critique, value strategy, conceptual first-inference |
| **Highest-capability artifact** | Fable | the spec — the one artifact everything downstream obeys (`/proto-spec`) |
| **Draft / build / verify** | Sonnet 4.6 | implementation, testing, most interactive skills, the drafter half of draft/critique |
| **Mechanical** | Haiku 4.5 | git, checklists, state persistence, demo-readiness gates, no-build single-file spikes |

Set `model:` in each skill/agent frontmatter so the switch takes effect on invocation. **Anti-pattern:** using Opus to *type* (produce volume). Use it to *judge* — to fix a cheaper model's first draft. (Re-verify model IDs each release; aliases like `sonnet`/`opus` track the latest automatically.)

---

## 7. Hooks & permissions

Hooks fire deterministically around tool use; they enforce gates without spending agent tokens and can filter noisy output before it enters context.

| Event | Fires | Good uses |
|---|---|---|
| `PreToolUse` | before a tool runs (can block via exit 1 / rewrite args) | sanitize/deny dangerous Bash, validate edits |
| `PostToolUse` | after a tool succeeds | **format on edit (Prettier)**, compress a 10k-line log to a 200-line error summary |
| `Stop` | turn/session end | **build gate** — block turn-end until `npm run build` passes |
| `SessionStart` | session begins | load state, orient |
| `UserPromptSubmit` | user message | transform/augment input |

Your harness already does the two highest-value ones correctly: PostToolUse Prettier on `Edit|Write`, and a Stop hook that runs the build and tails only the last 20 log lines on failure (`exit 2` to block) — exactly the "filter output before context" pattern. Keep it. For MVP tier, upgrade the Stop hook to lint + test + build.

**Permissions** (`settings.json`, evaluated deny → ask → allow, first match wins, deny always wins):
- **allow:** dev server, build, lint, test, `git add/commit/status/diff/log`, `npx shadcn`
- **ask:** `npm install` and bare `npx` (verify the package exists on npm first — a meaningful share of AI-suggested packages don't exist), anything touching `.env`
- **deny:** `git push --force`, `Read(.env*)`, production deploys

Put team policy in `settings.json`; machine-specific overrides in `settings.local.json` (uncommitted).

---

## 8. MCP servers

Configure in `.mcp.json` (project scope, committed — teammates approve on first run) or `~/.claude/settings.json` (user scope). Keep secrets in `settings.local.json` or user scope, never in the committed file.

**Browser-tool role split (important):** Playwright **drives** (navigate, click, fill, assert) → use for E2E and core-flow verification. Chrome DevTools **observes** (console, network, screenshots) → inspection and debugging only. Never drive with DevTools.

Per-project default (written at scaffold time):
```json
{ "mcpServers": {
  "context7":       { "type": "stdio", "command": "npx", "args": ["-y", "@upstash/context7-mcp"] },
  "chrome-devtools":{ "type": "stdio", "command": "npx", "args": ["chrome-devtools-mcp@latest"] },
  "playwright":     { "type": "stdio", "command": "npx", "args": ["-y", "@playwright/mcp@latest"] }
}}
```
**Token watch:** audit `/context` per project — MCP tool schemas are the main bloat source. Disable unused servers via `/mcp`; the removed `sequential-thinking` server is a good example (redundant with native extended thinking).

---

## 9. The test gate

The quality mechanism. Layered; any red fails the wave; all results witnessed via tool calls.

1. **Example tests** (Vitest) — one per SPEC.md Given/When/Then scenario, verbatim.
2. **Property tests** (fast-check) — domain invariants from DOMAIN.md; ≥1 per core-domain module; pin counterexamples as permanent examples. Core domain logic lives in `src/domain/` as pure functions (zero UI imports) so it's trivially testable.
3. **Interaction tests** (Playwright) — the feature's user-visible outcome when actually clicked.
4. **E2E core flow** (Playwright) — the Value Moment sequence, run at verify time with property tests at high `numRuns`.

Never edit a test to make it pass. Expect 2–3 red→green loops per feature — that's the harness working.

---

## 10. Compounding & the registry (cross-project reuse)

Three horizons:
- **Within project:** `docs/LEARNINGS.md` (append-only) + promoted CLAUDE.md rules + Claude Code auto memory (`~/.claude/projects/<proj>/memory/MEMORY.md`).
- **Across projects — component registry:** a personal public GitHub repo with root `registry.json` (any public repo is a shadcn registry). `/compound` flags anything built twice; promote it, then `npx shadcn@latest add <you>/<repo>/<item>` in the next project. The same repo doubles as a **plugin marketplace** for your skills/agents.
- **Across projects — the harness itself:** version it with git tags; when a rule/skill proves out in two projects, upstream it.

`/compound` asks three questions every build: what shouldn't the next prototype relearn; what's reusable (built twice = promote); what one rule would have prevented today's biggest time sink. Package a stable harness as a **plugin** (`.claude-plugin/plugin.json` bundling skills + agents + hooks + MCP) when you want one-command install across a team.

---

## 11. Tier model — know what you're building

Declare the tier in `PROGRESS.md` at kickoff. (#1 industry mistake: shipping prototype code as production. #2: over-polishing a prototype destined for rebuild.)

| Tier | Goal | Quality bar | Skip |
|---|---|---|---|
| **Prototype** | test desirability/UX, demo | looks excellent, happy path works, realistic seed data | auth hardening, deep error handling, full test pyramid |
| **MVP** | smallest shippable for real users | + real auth/persistence, error/loading/empty states, E2E smoke, screenshot baselines | scale, multi-tenancy polish |
| **Production** | reliability/security/maintainability | full playbook | nothing |

---

## 12. Token-efficiency playbook (consolidated)

- **Budget the always-on layer.** CLAUDE.md + AGENTS.md + skill/agent descriptions + MCP schemas are paid every turn. Keep CLAUDE.md <60 lines; trim dead files; cap user-scope MCP to 1–2.
- **Lean on progressive disclosure.** Skills cost only their description until triggered — prefer many small skills over one giant always-on rulebook.
- **Isolate with subagents.** Push research/review/audit into subagents; the main thread receives summaries, not transcripts.
- **Read sections, parallelize, don't re-verify.** offset+limit on large files; issue independent tool calls together; never re-read a file just to confirm an edit landed.
- **`/clear` between features; `/context` to audit; keep cache anchors stable** (DOMAIN/SPEC/design-system) so they stay cached.
- **Filter at the hook.** Compress noisy command output in PostToolUse before it reaches context.

---

## 13. Starter scaffold & setup checklist

```bash
# 1. Copy the harness (.claude/, .mcp.json, instruction files) into the new project root
# 2. Scaffold app + design system
npx shadcn@latest init --preset <your-preset-code>
npx skills add shadcn/ui
npm i motion d3                 # + @observablehq/plot for standard charts
# 3. Drive the pipeline
#   /proto-build "<one line or detailed brief>"
```

Health checklist:
- [ ] CLAUDE.md <60 lines (`@AGENTS.md`); AGENTS.md <100; design-system.md has exact values, not adjectives
- [ ] Subagent routing wired (planner / code-reviewer / ui-debugger); models set per agent
- [ ] `.mcp.json`: playwright, chrome-devtools, context7 (+ shadcn) configured and responding
- [ ] Test gate proven: a deliberately broken domain function fails the suite; a property test catches a seeded invariant violation
- [ ] Stop hook blocks on broken build; PostToolUse formats on edit
- [ ] Permissions: allow build/test/commit; ask for installs/.env; deny force-push
- [ ] Personal registry repo exists (`registry.json`); `/compound` runs and writes LEARNINGS.md every build
- [ ] Delete dead files (e.g. the deprecated `design-reviewer` agent — its description is paid every turn)
- [ ] Quarterly: re-audit the harness against the newest model; delete scaffolding it no longer needs

---

## 14. Re-verify periodically (dated items)

- **Model IDs** (`claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`) are early-2026 snapshots; confirm each release. Prefer aliases (`opus`/`sonnet`/`haiku`/`fable`) where you want auto-tracking.
- **"Fable" is real, not an error** — it's a valid model alias in the current environment and `/proto-spec` correctly routes to `claude-fable-5` for the highest-leverage artifact. (An automated digest flagged it as a typo; that flag is wrong.)
- **Stack pins** (Next.js 16, Tailwind v4, shadcn CLI v4, Playwright/DevTools `@latest`) — verify patch updates don't break `/proto-init`.
- **Stats** ("under-200-lines → 92% adherence", "share of AI-suggested packages that don't exist") drift with model improvements — treat directionally.
- **AGENTS.md native support** — Claude Code's first-class reader is CLAUDE.md; the `@import ./AGENTS.md` bridge is the reliable pattern. Re-check if native AGENTS.md ingestion ships.

---

## Sources
- [Effective context engineering for AI agents — Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Introducing advanced tool use — Anthropic](https://www.anthropic.com/engineering/advanced-tool-use)
- [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices)
- [Memory / CLAUDE.md](https://code.claude.com/docs/en/memory) · [The .claude directory](https://code.claude.com/docs/en/claude-directory)
- [Subagents](https://code.claude.com/docs/en/sub-agents) · [Skills](https://code.claude.com/docs/en/skills) · [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Hooks guide](https://code.claude.com/docs/en/hooks-guide) · [Hooks reference](https://code.claude.com/docs/en/hooks)
- [Settings](https://code.claude.com/docs/en/settings) · [Permissions](https://code.claude.com/docs/en/permission-modes)
- [Plugins](https://code.claude.com/docs/en/plugins) · [MCP](https://code.claude.com/docs/en/mcp) · [Context window](https://code.claude.com/docs/en/context-window)
- Internal project docs: `CLAUDE_SETUP.md`, `RAPID-PROTOTYPING-HARNESS.md`, `prototype-harness/` skills & agents
