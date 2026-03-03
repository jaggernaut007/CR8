# Research Prompt: Best Coding Practices for Agentic AI Coding Agents
## + Claude Code Integration Guide

---

## ── PART 1: HOW TO SET THIS UP IN YOUR PROJECT ──────────────────────────────

### What Files to Create and Where

This prompt comes with a companion file package. Copy the following files into your project **before** running this research prompt. The agent will reference these structures throughout the guide it produces.

```
your-project/
├── AGENTS.md                          ← Universal agent memory (all tools)
├── CLAUDE.md                          ← Claude Code-specific memory + @imports
├── CLAUDE.local.md                    ← Personal/machine overrides (add to .gitignore)
├── PROGRESS.md                        ← Cross-session state file (agent updates this)
├── scripts/
│   └── init.sh                        ← Session smoke test (run at session start)
├── .claude/
│   ├── skills/
│   │   └── session-handoff/
│   │       └── SKILL.md               ← Session state management skill
│   └── agents/                        ← Custom subagent definitions (add your own)
└── docs/
    ├── adr/
    │   └── ADR-000-template.md        ← Architecture Decision Record template
    └── research/
        └── RESEARCH-TEMPLATE.md       ← Implementation research note template
```

### Step-by-Step Setup Instructions

**Step 1 — Install Claude Code** (if not already installed)
```bash
npm install -g @anthropic-ai/claude-code
```
Then run `claude` in your project root to initialise.

**Step 2 — Copy the template files**
Copy all companion files from the package above into your project. Fill in the `TODO` sections in `AGENTS.md` with your actual tech stack and commands.

**Step 3 — Fill in AGENTS.md**
Open `AGENTS.md` and replace every `[placeholder]` with real values:
- Your project name and description
- Your actual build/test/lint commands
- Your specific code standards
- Your key directory paths

**Step 4 — Make init.sh executable and configure it**
```bash
chmod +x scripts/init.sh
```
Then open `scripts/init.sh` and uncomment/adapt the sections for your stack. At minimum, configure the test runner and linter checks.

**Step 5 — Gitignore CLAUDE.local.md**
```bash
echo "CLAUDE.local.md" >> .gitignore
```
This file is for your personal machine only — never commit it.

**Step 6 — Enable Skills in Claude Code**
In your `CLAUDE.md` or project settings, ensure skills are enabled. Claude Code picks up skills automatically from `.claude/skills/`. You can verify with:
```bash
claude /agents   # List available agents and skills
```

**Step 7 — Set up symlinks for multi-tool consistency** (optional but recommended)
If you use Cursor, GitHub Copilot, or other tools alongside Claude Code:
```bash
# Cursor
mkdir -p .cursor/rules
ln -sfn ../../AGENTS.md .cursor/rules/main.mdc

# GitHub Copilot
ln -sfn AGENTS.md .github/copilot-instructions.md

# Windsurf
mkdir -p .windsurf
ln -sfn ../AGENTS.md .windsurf/rules.md
```
This means you maintain one source of truth — `AGENTS.md` — and all tools read from it.

**Step 8 — Verify the setup**
Run your first Claude Code session:
```bash
claude
```
Then type:
```
Read AGENTS.md and PROGRESS.md and tell me what you understand about this project.
Run ./scripts/init.sh and report any failures.
```
If Claude correctly describes your project and init.sh passes, the setup is working.

### Your Session Workflow (After Setup)

**Starting a session:**
```
Read PROGRESS.md for current state, then run ./scripts/init.sh to verify the app is healthy.
```

**Ending a session:**
```
Use the session-handoff skill to update PROGRESS.md with what was done this session, 
what's in progress, and what the next steps are.
```

**Starting a new feature:**
```
Use Plan mode to create an implementation plan for [feature]. 
Check docs/adr/ for any relevant architectural decisions first.
Do not write any code until I have approved the plan.
```

**Before using an external library:**
```
Before implementing, read docs/research/[library].md if it exists. 
If it doesn't exist, research the official docs for [library] v[X] and 
create a research note at docs/research/[library].md using the RESEARCH-TEMPLATE.md format.
Then implement based on the research note, not from memory.
```

---

## ── PART 2: THE RESEARCH PROMPT ─────────────────────────────────────────────

### Mission Statement

You are tasked with producing a **comprehensive, practitioner-grade guide** on best coding practices specifically designed for agentic AI coding workflows. This is NOT a generic "clean code" guide — it must address the unique failure modes, context dynamics, and structural requirements that emerge when an AI agent (not a human) is the primary code author and executor across multiple sessions.

Assume the reader:
- Actively uses Claude Code (or Cursor/Codex/RooCode)
- Has already set up the file structure described in Part 1 above
- Understands basic software engineering
- Uses MkDocs (Material theme) for documentation
- Wants to know what changes when AI does the heavy lifting

The guide should integrate directly with the file structure above — reference `AGENTS.md`, `PROGRESS.md`, `CLAUDE.md`, `scripts/init.sh`, `docs/adr/`, and `docs/research/` throughout the guidance.

---

### Research Scope

Research and write detailed, actionable guidance across the following eight domains. For each domain, go beyond what the agent already knows from training data — surface edge cases, anti-patterns, counterintuitive findings, and production-grade recommendations.

---

#### 1. AGENTS.md / CLAUDE.md Architecture: The Agent Memory Layer

This is the most critical infrastructure layer and is widely misunderstood.

**Research and cover:**
- The difference between `AGENTS.md` (universal, multi-tool standard now maintained under the Linux Foundation) vs `CLAUDE.md` (Claude-specific, with `@import` support) vs `CLAUDE.local.md` (personal/dev-machine overrides). Explain when to use each and how to symlink for consistency across tools.
- The **system-reminder injection caveat**: Claude wraps `CLAUDE.md` content in a system reminder that tells the model to ignore content that isn't relevant to the current task. This means large, unfocused files actively hurt performance — Claude will discard your instructions. Ideal size is under 100 lines. Investigate the implications.
- The **context window budget problem**: Claude Code's built-in system prompt already uses ~50 individual instructions. Your `CLAUDE.md` competes for reliable instruction slots. What belongs in the file vs in slash commands vs in skill files?
- Hierarchical loading: how the closest `AGENTS.md` to the file being edited takes precedence. How to architect this for monorepos.
- What categories of content are universally applicable (goes in root `AGENTS.md`) vs task-specific (goes in slash commands or skills) vs personal (goes in `CLAUDE.local.md`).
- The **negative instruction problem**: LLMs follow positive instructions more reliably than negative ones. "Avoid asking for personal information, instead refer the user to X" outperforms "Do NOT ask for personal information". How to rewrite negative rules.
- Auto-memory systems: when to let the agent maintain its own memory files vs curating them manually.
- The symlink strategy for multi-tool consistency (documented in Part 1 above — expand on the rationale and edge cases).
- **Anti-patterns to avoid**: Bloated files, task-specific instructions in universal files, duplicate guidance across files.

---

#### 2. Project & Directory Structure for AI Readability

Agents navigate code very differently from humans.

**Research and cover:**
- The **package explosion anti-pattern**: deep monorepo structures with many micro-packages cause agents to spend significant time just mapping dependencies. Preferred: flat structure with 2–3 top-level packages, then organise within those using folders — not additional packages. Quantify the performance difference if possible.
- Colocation principle: put tests, types, and documentation as close to the code they describe as possible.
- `README.md` files at the root AND in each significant directory: agents use these as orientation documents.
- `CONTRIBUTING.md`: document coding patterns, PR expectations, test coverage requirements, and naming conventions here.
- File naming conventions that aid agent navigation: explicit, descriptive names over clever/short ones. Avoid re-exports and barrel files — agents get confused by layers of indirection.
- Code Health as an AI-readiness metric: research the finding that agents perform measurably worse in low code-health codebases. Target code health scores of 9.5+.
- The AGENTS.md hierarchy for sub-directories: use directory-level `AGENTS.md` files to give agents scoped context.

---

#### 3. Context Management: Fighting Context Rot and Session Forgetting

The single biggest failure mode of agentic workflows is context degradation.

**Research and cover:**
- **Within-session context rot**: as conversations grow, earlier instructions get pushed out of effective attention. Strategies: use `/clear` or compact commands at natural breakpoints, open fresh sessions for new features.
- **Cross-session amnesia**: agents have zero memory between sessions. Architecture your project so the agent can get oriented fast — via `AGENTS.md`, `README.md`, and `PROGRESS.md` (as set up in Part 1).
- The **initialiser + coding agent pattern**: use a separate initialiser step (`scripts/init.sh`) that verifies environment state before any coding begins.
- **Session handoff artifacts**: the `PROGRESS.md` pattern (already created in Part 1) — what to write, how specific to be, and what the next session reads first. Reference the `session-handoff` skill.
- **Context isolation with subagents**: using the Explore subagent for read-only codebase navigation, the Plan subagent for architecture decisions, and dedicated implementation agents for execution.
- The **windowed context anti-pattern**: passing full conversation history to subagents usually breaks things. Prefer explicit structured summaries.
- **Context hiding**: how to scope what each agent/subagent sees. Subagents should receive the minimum context needed.

---

#### 4. Avoiding Hallucinations and Speculative Code Generation

Agents hallucinate APIs, invent library methods, and confidently write broken code.

**Research and cover:**
- **The "mark as complete without testing" failure mode**: agents commonly skip end-to-end verification. The `AGENTS.md` Definition of Done (already in the template from Part 1) addresses this — explain why it works and common bypass patterns to watch for.
- **Providing testing tools, not just instructions**: giving the agent access to browser automation (Puppeteer MCP), curl commands, and test runners dramatically reduces hallucination.
- **The `scripts/init.sh` pattern** (from Part 1): how smoke tests catch broken foundation states before they compound. Design principles for an effective init script.
- **API documentation injection**: the `docs/research/` pattern (from Part 1) for pre-researching external libraries. Why this beats the agent using training data. Reference `RESEARCH-TEMPLATE.md`.
- **Test-as-documentation**: use well-written tests as the primary specification for how functions and components should behave.
- **Language/ecosystem selection for reduced hallucination**: Go vs Python vs JavaScript — which ecosystems are most AI-friendly and why.
- **Explicit over implicit code patterns**: avoid "magic" — implicit behavior, global state, decorator-heavy patterns.
- The **self-verification prompt**: instruct the agent to read back the change it made and explain what it did before marking a task complete.

---

#### 5. Skill Files and Modular Agent Knowledge

Agent Skills are the evolution beyond prompt templates.

**Research and cover:**
- The architecture of a Skill: a directory with a `SKILL.md` as entry point plus optional scripts and templates. Explain YAML front matter, naming conventions, and directory placement (`~/.claude/skills/` for global, `.claude/skills/` for project-scoped).
- **On-demand loading**: only Skill metadata is preloaded into context. Full `SKILL.md` is read when the Skill becomes relevant. Design implications.
- The **context window is a public good** principle: Skills compete for tokens. Keep them concise.
- Skill development workflow: use "Claude A" to write and refine the Skill, test with "Claude B" on real tasks, iterate.
- When to create a Skill vs a slash command vs a subagent vs an AGENTS.md rule.
- Converting your MkDocs documentation into Skills: extract procedural knowledge and turn it into agent-executable Skills.
- The `session-handoff` skill (from Part 1) as a worked example — explain its design decisions.
- Signs a Skill is poorly designed: agent repeatedly reads the same section, skips bundled reference files, asks clarifying questions the Skill should have answered.

---

#### 6. MkDocs Documentation Architecture for Agent Consumption

Your MkDocs docs are an asset — design them so agents can extract value, not just humans.

**Research and cover:**
- The **dual-audience problem**: humans skim docs; agents need to be pointed at specific docs and retrieve precise information.
- Structure every page with a machine-readable header: what this doc covers, what files it pertains to, and what the agent should do after reading it.
- **Cross-reference architecture**: every doc page should explicitly link to related implementation files. Agents follow references; without them, they guess.
- **The ADR pattern** (from Part 1): maintain `docs/adr/` and reference it from `AGENTS.md`. When agents ask "why was this built this way?", they find the answer in an ADR. Reference `ADR-000-template.md`.
- **The research note pattern** (from Part 1): `docs/research/` as the pre-implementation knowledge base. Reference `RESEARCH-TEMPLATE.md`. How this prevents re-researching the same questions.
- **The living README strategy**: co-locate `README.md` in each major directory, auto-include them in MkDocs using `mkdocs-include-markdown-plugin`.
- **Changelog and PROGRESS.md**: how `PROGRESS.md` (from Part 1) creates an auditable trail and orients future sessions.
- **What agents can't get from docs alone**: complex runtime behaviour, environment-specific configurations, external API quirks. Document these explicitly with examples.

---

#### 7. Project Management to Code Translation

The gap between "what we want to build" and "what the agent can reliably execute" is a planning problem.

**Research and cover:**
- **Specification-driven development**: before any code is written, produce a written spec with input/output contracts, edge cases, error states, and explicitly what is out of scope.
- **Task decomposition for agents**: agents perform best on tasks achievable within a single session (~30–60 min of agent work). Decompose large features into independently completable subtasks.
- **GitHub Issues as agent task units**: one issue per agent task. Include context, acceptance criteria, files likely touched, and links to relevant ADRs.
- **Plan mode before implementation**: use Claude's Plan mode to produce an implementation plan before writing code. Review and approve before proceeding.
- **Feature flagging for incremental delivery**: agents build incrementally. Use feature flags so each piece can be merged safely.
- **Definition of Done for agent tasks**: reference the DoD in `AGENTS.md` (Part 1 template) — explain why each element is there and how to customise it.
- **Two-tier agent architecture**: Orchestrator maintains context and breaks tasks; Subagents execute isolated subtasks. Why three-tier hierarchies fail in practice.

---

#### 8. Technical Research Practices for Implementation

When agents need current or specialised knowledge, guessing from training data produces hallucinations.

**Research and cover:**
- **Research before implementation, not during**: the `docs/research/` workflow (Part 1) — run a dedicated research pass and produce a research note before any implementation begins.
- **The `RESEARCH-TEMPLATE.md` pattern** (from Part 1): what goes in each section and why. Walk through a concrete example (e.g. researching a Stripe API integration).
- **The retrieval-augmented implementation pattern**: inject official documentation as context before the agent begins. More reliable than training data.
- **Verification checkpoints**: for third-party services — read docs → write minimal proof-of-concept → run and verify → build full implementation. Never skip step 3.
- **Pinning library versions in research context**: always specify exact version. LLMs mix APIs across versions.
- **The "what changed" research prompt**: for known libraries that may have updated APIs.
- **Web search integration**: configure the agent to search official documentation for critical integration decisions.

---

### Additional Sections (Topics Commonly Missed)

Include the following additional sections:

#### Observability and Debugging Agent Behaviour
- Log verbosity calibration: too much wastes tokens; too little makes debugging impossible.
- Using a logging proxy between your agent harness and the API (via `ANTHROPIC_BASE_URL`) to observe what's actually in context — essential for debugging why the agent ignores instructions.
- Tracing agent tool calls: maintain trace logs to understand which tools the agent invoked and in what order.

#### Code Review Practices for Agent-Generated Code
- Agent-generated code should go through the same PR review process as human-written code.
- Cross-model review: use a different model for reviewing than for writing. Claude for execution, GPT/o-series for review/bugs — this dynamic consistently catches more issues.
- Set up automated linters with a Stop hook that runs on every agent output. Don't ask the agent to fix formatting — automate it and feed only errors back.

#### Cost and Efficiency Management
- Token budgeting: track token usage per session type. Identify which sessions consume the most tokens.
- Model routing: use faster, cheaper models (Haiku, Sonnet) for exploration and read-only tasks; reserve capable models for complex reasoning.
- Tool response latency: a test that takes 3ms vs 5 seconds is a significant difference in agentic workflows. Optimise your build pipeline for fast feedback.

#### Security and Guardrails
- Never give agents write access to production systems, databases, or secrets.
- Use isolated sandboxes (Docker containers, ephemeral environments) for agent execution.
- Version control everything: prompts, `AGENTS.md`, Skills, slash commands, and evaluation datasets.
- Implement human-in-the-loop checkpoints for irreversible actions. Define these in `AGENTS.md`.

#### Testing Strategy for Agent-Driven Development
- Tests are ground truth. The agent cannot argue with a failing test.
- Tests as specification: write tests to be readable as requirements, not just verification.
- E2E tests are more valuable than unit tests in isolation for agent workflows.
- **The "broken foundation" problem**: always run the smoke test (`scripts/init.sh` from Part 1) before beginning new work.

---

### Output Format Requirements

Produce this guide in a format suitable for integration into an existing MkDocs documentation site. Specifically:

- Use MkDocs-compatible Markdown with proper heading hierarchy (H2 for major sections, H3 for subsections)
- Include a `nav:` metadata block at the top suggesting where this fits in an MkDocs navigation structure
- Reference the actual file paths established in Part 1 throughout (e.g. `AGENTS.md`, `PROGRESS.md`, `scripts/init.sh`, `docs/adr/`, `docs/research/`)
- Use admonition blocks (MkDocs Material theme syntax: `!!! tip`, `!!! warning`, `!!! danger`) to call out critical anti-patterns and high-value recommendations
- Include concrete code examples, file structure examples, and template content in fenced code blocks
- End each major section with a checklist: "Before moving on, verify you have: [...]"
- Include a master checklist at the end covering the entire guide
- Write in a direct, practitioner tone — no fluff, no "it depends" without immediately explaining what it depends on and what to do in each case

### Scope Boundaries

**Do NOT cover:**
- Basic clean code principles the agent already knows (DRY, SOLID, naming conventions in isolation)
- Generic CI/CD pipeline setup unrelated to agent workflows
- Comparisons of which AI tool to use
- AI safety topics beyond immediate coding agent guardrails

**DO prioritise:**
- Anything counterintuitive — where the right approach for AI agents differs from human developers
- Findings backed by empirical observation, not just theory
- Content that ties back to the actual files created in Part 1 of this document
- Failure modes and how to detect them before they compound
