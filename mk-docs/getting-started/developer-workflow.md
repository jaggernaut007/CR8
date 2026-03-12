# Developer Workflow (Claude Code)

This guide is the practical day-to-day reference for working on CR8 with Claude Code as your primary coding agent. Follow it every session — the rituals exist because they prevent an entire class of common mistakes.

!!! note "What this page covers"
    Claude Code setup for new developers, the session start/end rituals, feature development workflow, external library handling, architectural decisions, prompt changes, and copy-paste ready agent prompts.

---

## Claude Code Setup (First Time Only)

Claude Code is the primary AI coding agent for this project. It is not installed by default.

### Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

### Start your first session

Navigate to the project root and launch Claude Code:

```bash
cd /path/to/CR8
claude
```

### Verify setup

On first launch, paste this prompt to orient Claude Code to the project:

```
Read PROGRESS.md and AGENTS.md and tell me what you understand about this project.
Then run ./scripts/init.sh.
```

Claude Code will read the project memory files and run the health-check script. Verify that all checks in `init.sh` pass before doing anything else.

!!! tip "AGENTS.md is the source of truth"
    `AGENTS.md` is the universal agent memory file loaded by Claude Code, Copilot, Cursor, and Codex. It describes the stack, standards, testing requirements, and the definition of done. Claude Code reads it at the start of every session via `CLAUDE.md`.

---

## Session Start Ritual

Run this ritual at the start of **every** working session, without exception.

### Step 1 — Read PROGRESS.md

```
Read PROGRESS.md and summarise where we left off.
```

`PROGRESS.md` is the canonical handoff document. It tells you what was last completed, what is in progress, and what is blocked.

### Step 2 — Run init.sh

```bash
./scripts/init.sh
```

`init.sh` verifies that the environment is healthy: dependencies installed, lint clean, all 626 tests passing. If any check fails, **fix it before starting new work**.

!!! warning "Never skip init.sh"
    Starting new work on top of a broken baseline compounds problems. If `init.sh` fails, treat fixing it as task zero.

### Step 3 — Check context usage

Use the Claude Code slash command to inspect token usage before diving in:

```
/context
```

If context is already heavy from a prior session, use `/compact` to summarise before starting.

---

## Feature Development Workflow

### Plan before coding

For any task with 3 or more steps, activate Plan mode before writing a single line of code.

**In Claude Code, press `Shift+Tab` to enter Plan mode.**

Prompt Claude with the task:

```
Use Plan mode to implement [feature]. Check docs/adr/ for relevant decisions first.
```

Claude Code will produce a written plan. **Read it carefully and approve it** before Claude writes any code. Catch misunderstandings at the planning stage, not after 200 lines of implementation.

!!! tip "Plan mode is mandatory for non-trivial work"
    If a task touches more than one file or has conditional logic, use Plan mode. The 30-second investment in planning saves far more time in rework.

### Implement and verify

After implementation:

```bash
make lint && make test
```

Both must pass before you commit. This is the definition of done — see `AGENTS.md`.

!!! info "Code quality standards"
    All new code must follow the [Code Quality Guide](../contributing/code-quality.md): short functions (max 25 statements), structured logging in every module, Google-style docstrings, and lazy log formatting. These are enforced by Ruff rules and Claude Code agent rules — `make lint` will catch violations.

### Commit with conventional commits

Use the conventional commit format for every commit:

| Prefix | Use for |
|--------|---------|
| `feat:` | New feature or capability |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `chore:` | Tooling, deps, config, formatting |
| `test:` | Adding or updating tests |
| `refactor:` | Code change with no behaviour change |

**Example commits:**

```bash
git commit -m "feat: add PPT output format to generate agent"
git commit -m "fix: sanitize em-dash in pdf_builder Unicode map"
git commit -m "docs: update developer workflow with prompt changes section"
```

### Commitizen — semantic versioning

Use `cz commit` for interactive conventional-commit prompting (enforced by the pre-commit hook):

```bash
cz commit          # interactive prompt — structures your commit message
cz bump            # bump version + update CHANGELOG.md + create git tag
cz changelog       # regenerate CHANGELOG.md without bumping version
```

To cut a release:

```bash
cz bump --changelog
git push && git push --tags
```

!!! tip "Why cz commit instead of git commit?"
    `cz commit` prompts you through the conventional-commit format and rejects invalid messages before they reach the hook. Use it for all commits — the pre-commit hook will warn you if you bypass it with a non-conventional message.

### Reset context after every commit

```
/clear
```

Run `/clear` after every commit to reset the Claude Code context window. Long context accumulates noise and increases the risk of Claude making decisions based on stale information.

---

## MCP Servers

Claude Code connects to MCP (Model Context Protocol) servers that extend agent capabilities beyond the codebase.

### Available MCPs

| MCP Server | What It Does | Used By |
|------------|-------------|---------|
| **Context7** | Version-specific library docs (LangGraph, FastAPI, ChromaDB, python-pptx, fpdf2, MoviePy, PyMuPDF, 1000+) | `research-assistant`, `docs-writer` |
| **Playwright** | Browser automation — navigate, click, snapshot, console/network inspection | `code-reviewer`, `debug-detective`, `docs-writer` |
| **Sequential Thinking** | Structured step-by-step reasoning with branching and revision | `adr-writer`, `research-assistant`, `docs-writer` |
| **CodeGrok** | Semantic code search via embeddings — find code by meaning, not keywords (10-100x token savings) | All agents |
| **code-graph-mcp** | Structural code analysis — call graphs, imports, callers/callees, complexity, dependency maps | `code-reviewer`, `debug-detective`, `research-assistant` |

### When MCPs are used automatically

You don't need to call MCPs manually — agents invoke them at the right step:

- **Researching a library?** `research-assistant` calls Context7 in Step 0 before falling back to web search. It also runs a mandatory security assessment (CVE check, license audit, maintenance health, dependency tree) and uses Sequential Thinking to evaluate security trade-offs when adding new dependencies.
- **Reviewing frontend changes?** `code-reviewer` uses Playwright to navigate `localhost:8080` and verify the UI renders correctly.
- **Debugging a UI bug?** `debug-detective` uses Playwright to check console errors and failed network requests.
- **Writing an ADR?** `adr-writer` uses Sequential Thinking to reason through alternatives before drafting.
- **Updating docs?** `docs-writer` uses Context7 to verify library API signatures are current. For new or significantly restructured pages, it uses Playwright to confirm the page renders correctly at localhost:8000. Sequential Thinking is available when a large change touches 5+ doc pages.
- **Understanding codebase structure?** Any agent can use CodeGrok (`get_sources`) to find relevant code by meaning (e.g., "how does video pipeline work?") instead of loading entire files.
- **Impact analysis before refactoring?** `code-reviewer` uses code-graph-mcp (`find_callers`, `dependency_analysis`, `complexity_analysis`) to understand what will break.

### Verify MCPs are connected

At session start, run `/mcp` to check all servers show green. If any are disconnected, re-add them:

```bash
# Context7 (project-scoped)
claude mcp add context7 -- npx -y @upstash/context7-mcp

# Playwright (project-scoped)
claude mcp add playwright -- npx -y @playwright/mcp@latest

# Sequential Thinking (user-scoped)
claude mcp add --scope user sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking
```

CodeGrok and code-graph-mcp are configured in `.claude/mcp.json` (project-scoped, auto-loaded).

### Code Intelligence: Re-indexing

- **code-graph-mcp**: Auto-reindexes on file changes via file watcher (2-second debounce). No manual action needed.
- **CodeGrok**: Run `make reindex` after adding/removing files, or after merging branches with structural changes. Uses `learn` tool with `mode=auto` for incremental updates.

!!! tip "MCPs require Node.js >= v18"
    Context7, Playwright, and Sequential Thinking run via npx. Ensure Node.js v18+ is installed. CodeGrok and code-graph-mcp are Python-based (3.10+).

---

## External Library Workflow

Before using any external library or API in code, follow this protocol. Do not guess at an API — check the research notes first.

### Step 1 — Check the research index

```bash
cat docs/research/INDEX.md
```

Or prompt Claude Code:

```
Check docs/research/INDEX.md for any existing notes on [library] before I implement anything.
```

### Step 2 — If no note exists, research first

```
Use the research-assistant agent to research [library] v[X] before I implement anything.
```

The research assistant will search for current official documentation and pin the version in a note under `docs/research/`. For new dependencies, it also runs a mandatory security assessment: CVE scan, license compatibility check, maintenance health (last release date, maintainer count), and transitive dependency tree size. A note without a security section is considered incomplete.

### Step 3 — Implement only after the research note exists

```
Now that the research note is in docs/research/, implement [feature] using [library].
```

!!! warning "Do not implement external integrations without a research note"
    Library APIs change between versions. A research note pinned to the version in `pyproject.toml` prevents implementing against a stale API from training data. For new dependencies, the note must include a security assessment — a missing security section blocks implementation.

---

## Architectural Decisions

### Before changing structure

Before making any structural change — new dependency, changing pipeline structure, new output format — check the ADR log:

```bash
ls docs/adr/
```

Or prompt Claude Code:

```
Check docs/adr/ for any decisions relevant to [proposed change] before I proceed.
```

### ADR triggers

Create an ADR when any of the following are true:

- Adding a new pip dependency
- Changing the LangGraph pipeline structure (nodes, edges, state schema)
- Adding a new output format (PDF, PPT, Script, Video, or new)
- Changing the model routing logic in `backend/services/llm.py`
- Adding a new external service integration

### Creating an ADR

```bash
cp docs/adr/ADR-000-template.md docs/adr/ADR-XXX-short-title.md
```

Fill in the template: context, decision, alternatives considered, consequences. Commit the ADR before implementing the change.

```
I need to add a new output format. Use Plan mode and check CONTRIBUTING.md and docs/adr/ first.
```

---

## Prompt Changes

Prompts live in `backend/prompts/`. Never put prompt strings inline inside agent files.

### Workflow for changing a prompt

**1. Edit the prompt file**

```bash
# Example: editing the generate agent prompt
nano backend/prompts/generate.py
```

**2. Create a named variant for eval**

Give the variant a short name (e.g., `v2`, `concise-v1`).

**3. Run the eval comparison**

```bash
python -m backend.evals run_ab --variant [name]
```

**4. Review the results**

```bash
ls backend/evals/reports/
```

Open the report and compare the new variant against the production baseline.

**5. Commit only if the new variant wins or draws**

!!! warning "Never commit a prompt regression"
    If the eval shows the new variant is worse on any criterion, do not commit it. Iterate on the prompt and re-run the comparison.

---

## Skills Reference

Claude Code skills are compound workflows invoked with `/skill-name`. They orchestrate multiple agents and checks in sequence.

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `/commit-ready` | "am I ready to commit" | Runs the full CONTRIBUTING.md checklist: lint, tests, docs staleness, PROGRESS.md, code review gate. Stops at first blocking failure. |
| `/coverage-report` | "what's my coverage" | Runs pytest-cov, ranks modules below 80% coverage, routes the weakest file to the test-writer agent with specific uncovered lines. |
| `/new-feature` | "scaffold a feature" | Classifies your feature (service/agent/endpoint), checks for ADR and research prerequisites, produces an ordered creation checklist across all required locations. |
| `/session-handoff` | "wrap up" | Writes or reads structured session state to/from PROGRESS.md. |

!!! tip "Skills chain together"
    `/new-feature` ends by suggesting `/commit-ready`. `/coverage-report` routes directly to the test-writer agent. Use them as a natural workflow: scaffold → implement → check coverage → commit-ready → commit.

---

## Session End Ritual

### Step 1 — Run the session handoff

```
/session-handoff
```

This triggers the `session-handoff` skill. Claude Code will update `PROGRESS.md` with a summary of what was done, what is in progress, and any blockers discovered during the session.

### Step 2 — Commit everything

```bash
make lint && make test
git add -p
git commit -m "chore: session end — [brief summary]"
```

### Step 3 — Clear context

```
/clear
```

End every session with `/clear`. This keeps the next session starting fresh.

---

## Useful Agent Prompts

Copy and paste these directly into Claude Code.

### Session start

```
Read PROGRESS.md and AGENTS.md and tell me what you understand about this project.
Then run ./scripts/init.sh.
```

### Plan a feature

```
Use Plan mode to implement [feature]. Check docs/adr/ for relevant decisions first.
```

### Research before implementing

```
Use the research-assistant agent to research [library] v[X] before I implement anything.
Check docs/research/INDEX.md first to see if a note already exists.
```

### Pre-commit validation

```
/commit-ready
```

Runs the full CONTRIBUTING.md checklist automatically. For manual review instead:

```
Review my recent changes before I commit. Check the code-reviewer agent checklist.
Run make lint and make test and show me the output.
```

### Scaffold a new feature

```
/new-feature
```

Walks through classification, ADR/research prerequisites, and produces a file creation checklist. For output formats specifically:

```
I need to add a new output format to the pipeline. Use Plan mode and check
docs/adr/ and CONTRIBUTING.md before writing any code.
```

### Change a prompt

```
I want to update the [agent name] prompt. Walk me through the eval workflow
in docs/evals/ before making any changes. Do not commit until we compare variants.
```

### Architectural change

```
I want to [proposed change]. Before writing any code, check docs/adr/ for
relevant decisions and create a new ADR if this is a structural change.
```

### Debug a failing test

```
The test [test_name] in [test_file] is failing. Read the test file and the
source it tests, identify the root cause, and propose a fix. Do not
change test assertions to make the test pass — fix the underlying code.
```

### Check test coverage

```
/coverage-report
```

Runs pytest-cov and identifies under-tested modules. Routes the weakest file to the test-writer agent.

### Update docs before committing

```
Update the docs for my recent changes before I commit.
```

The `docs-writer` agent reads your staged files, finds the corresponding `mk-docs/` pages, and updates them. If the pre-commit hook warns about missing docs (`⚠️ Docs check:`), run this prompt first.

### Session handoff

```
/session-handoff
```

### Reset a stuck session

```
/clear
```

Then start a fresh session with the session start prompt above.

---

## CI/CD

CR8 uses GitHub Actions for CI and deployment. See the [Deployment Guide](../deployment/gcp-cloud-run.md#cicd-pipeline) for full details.

**CI runs automatically** on every push to `main` and every PR — lint, pytest, and frontend build/vitest in parallel. All must pass.

**Deployment is manual** — go to Actions → Deploy → Run workflow, type `deploy`, and confirm. The workflow builds via Cloud Build, deploys to Cloud Run, and health-checks the live URL.

There are no service account keys in GitHub — authentication uses GCP Workload Identity Federation (OIDC).

---

## Make Commands Reference

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies via `uv sync --all-extras` |
| `make test` | Run the full 626-test suite with verbose output |
| `make lint` | Run `ruff check .` — must be clean before committing |
| `make lint-fix` | Run `ruff check . --fix` — auto-fix lint issues |
| `make dev` | Start FastAPI + Uvicorn at http://localhost:8080 (all interfaces, hot-reload) |
| `make serve` | Start FastAPI at http://localhost:8080 (localhost only, hot-reload) |
| `make run ARGS="file.pdf"` | Run the pipeline directly from the CLI |
| `make docs-serve` | Preview MkDocs documentation at http://localhost:8000 |
| `make docs-build` | Build documentation in strict mode (fails on warnings) |
| `make docker-build` | Build the Docker image locally |
| `make docker-run` | Run the Docker container locally on port 8080 |
| `make clean` | Remove `chroma_db/`, `outputs/`, and Python caches |

---

## Troubleshooting Common Issues

### `init.sh` fails at lint

```bash
make lint-fix
```

Ruff will auto-fix most issues. Re-run `./scripts/init.sh` to confirm clean.

### `init.sh` fails at tests

Read the test output carefully. Identify which test is failing and why. Fix the underlying code — do not modify test assertions to force a pass. Only start new work after all 626 tests are green.

### Claude Code ignores your instructions

Use `/clear` and start a fresh session. Long-running sessions accumulate context that can cause Claude to anchor on earlier decisions. Always start fresh sessions for new features.

### Context window getting crowded

```
/compact
```

Use `/compact` at natural breakpoints (after finishing a subtask, after a commit) to summarise the conversation without losing important context. Use `/clear` for a full reset.

### Claude proposes something that contradicts an earlier decision

```
Check docs/adr/ for any decisions relevant to [topic] before proceeding.
```

The ADR log is the authoritative record of architectural decisions. If an ADR exists for the topic, Claude must respect it. If the existing decision needs revisiting, create a new ADR first.

### `ModuleNotFoundError: No module named 'backend'`

The package was not installed in editable mode:

```bash
make install
```

### Pipeline test is slow / timing out

All LLMs, Tavily, and ChromaDB calls are mocked in tests. If a test is slow, it is likely making a real network call. Check that the test is using the shared fixtures from `conftest.py` and not bypassing mocks.

!!! tip "Zero real API calls is a hard requirement"
    The full 626-test suite runs in approximately 60 seconds with zero real API calls. Any test that hits a real endpoint is a bug in the test, not a valid slow test.
