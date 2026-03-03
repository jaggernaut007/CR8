# CLAUDE.md
<!-- Claude Code-specific memory. Kept lean — universal rules live in AGENTS.md.
     This file uses @import to pull in skill files on demand.
     Claude Code injects this into every session via system-reminder. -->

@import AGENTS.md

## Claude-Specific Behaviours

### Subagent Routing
- Use the **Explore** subagent for read-only codebase search — keeps navigation out of main context
- Use the **Plan** subagent before implementing anything non-trivial — always plan before coding
- Do NOT spawn subagents for simple single-file changes

### Context Management
- When context feels crowded or you've been working for many turns, stop and write a summary to `PROGRESS.md` before continuing
- Start fresh sessions for new features — don't continue sprawling threads
- If you are uncertain about a past decision, check `docs/adr/` before guessing

### Testing Protocol
- Always use tool calls to verify your work — read test output, don't assume it passes
- For web features, use browser automation to test as a real user would
- Run `./scripts/init.sh` at session start and after major changes

### Hallucination Prevention
- For any external library or API, check `docs/research/` first
- If research docs don't cover it, perform a web search for the current official docs before writing implementation code
- Pin library versions in all research queries — do not assume the latest API matches training data

## Skills Available
<!-- Skills are loaded on-demand — only metadata is preloaded -->
- `session-handoff` — write/read session state between conversations
- Add your own skills in `.claude/skills/`
