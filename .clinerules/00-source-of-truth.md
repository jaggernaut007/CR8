# Source of truth — do not fork context

This repo is driven by multiple agent harnesses (Claude Code, Codex, Cline, Antigravity).
`AGENTS.md` at the repo root is the single source of truth for every tool.

- **Do not generate a Memory Bank.** The project context already exists as versioned artifacts —
  treat these as your Memory Bank:
  - `AGENTS.md` — stack, commands, Definition of Done, code standards. Authoritative; read first.
  - `PROGRESS.md` — session state. Read at session start, update at end.
  - `docs/adr/` — architectural decisions; check before changing structure.
  - `docs/research/` — research notes for external libraries/APIs; check before adding a
    dependency, create a note if missing.
  - `docs/agentic-guide.md` — the full agent workflow guide this repo follows.
- Same mistake made twice → add a one-line rule to `AGENTS.md` (portable), not to a
  tool-specific file.
- Output dense, direct text. Omit pleasantries.

## Skills & agents (Cline bridge)
The reusable skill/agent harness lives in the Claude Code user scope and is mirrored into
Cline's directories by `scripts/sync-cline-harness.py`:

- `~/.claude/skills/*` → `~/.cline/skills/*` (Cline skills — frontmatter `name` + `description`)
- `~/.claude/agents/*` → `~/Documents/Cline/Workflows/*` (Cline workflows)

Cline has no per-skill/per-agent `model:` field — it routes tiers via the Plan/Act split
(Plan = high-capability, Act = mid-tier) — so the script drops Claude-only frontmatter and
translates each `model:` alias into a body note. Cline's built-in subagents are read-only
research agents that are not user-customisable, which is why write-capable agents map to
workflows. Re-run `python3 scripts/sync-cline-harness.py` after editing the source; add
`--force` to overwrite hand-tuned Cline files.
