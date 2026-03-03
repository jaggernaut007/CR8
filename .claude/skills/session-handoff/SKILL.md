---
name: session-handoff
description: Use at the END of a working session to write a structured handoff document, or at the START of a session to read and orient from the previous session's state. Triggers on phrases like "wrap up", "end of session", "save progress", "what's the current state", "orient yourself".
---

# Session Handoff Skill

This skill manages structured state handoffs between agent sessions. It ensures no context is lost between conversations.

## When Writing a Handoff (End of Session)

Update `PROGRESS.md` with the following structure. Be precise — the next session reads this cold.

```markdown
## Current Status
**Last updated:** [TODAY'S DATE]
**Overall project phase:** [phase]

## What's Working
[List features verified end-to-end with test evidence]

## In Progress
[Specific file names, function names, what's done vs what's left]

## Known Broken / Blocked
[CRITICAL: list anything broken so the next session doesn't build on it]

## Next Steps (Prioritised)
1. [Most important thing]
2. [Second]
3. [Third]

## Recent Decisions
[Decisions made this session with brief rationale]
```

## When Reading a Handoff (Start of Session)

1. Read `PROGRESS.md` entirely
2. Run `./scripts/init.sh` to verify app state matches what's documented
3. If there is a mismatch (docs say "working" but tests fail), fix the broken state FIRST
4. Only then begin the new task

## Rules

- NEVER mark a feature complete in PROGRESS.md without having seen a test pass via tool call
- NEVER skip init.sh — if it's slow, that's information about your build pipeline, not a reason to skip
- If the previous session left something broken, document it clearly and fix it before building on it
- Keep PROGRESS.md entries specific: not "worked on auth" but "implemented JWT refresh token rotation in `src/auth/refresh.ts` — unit tests pass, E2E test pending"
