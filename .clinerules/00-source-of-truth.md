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
