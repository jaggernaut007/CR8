---
name: commit-ready
description: Full pre-commit readiness check. Runs the CONTRIBUTING.md checklist in order — lint, tests, docs staleness, PROGRESS.md, code review gate — and stops at the first blocking failure. Triggers on "am I ready to commit", "pre-commit check", "commit readiness", "ready to commit", "check before committing".
---

# Commit-Ready Skill

Validates the current working state against every condition in the CR8
CONTRIBUTING.md pre-commit checklist before you run `cz commit`.

Run this before any commit that touches `backend/` or `frontend/` source files.

## Step 1 — Identify what is staged

```bash
git diff --staged --name-only
```

If nothing is staged, report:
> Nothing is staged. Stage your changes with `git add` before running commit-ready.
Then stop.

Report the staged file list so the developer can confirm it looks right.

If ONLY `mk-docs/` or `.md` files are staged (docs-only commit), skip Steps 3 and 6 —
tests and code review are irrelevant for docs-only commits.

## Step 2 — Lint (BLOCKING)

```bash
make lint
```

**PASS**: Ruff reports no issues.
**FAIL**: Ruff reports violations.

On FAIL, stop and report:
> FAIL — Lint errors found. Run `make lint-fix` to auto-fix, then re-stage and re-run commit-ready.

Do NOT continue to subsequent steps on FAIL.

## Step 3 — Tests (BLOCKING)

```bash
make test
```

**PASS**: All tests pass and count is >= 362.
**FAIL**: Any test failure or error.

On FAIL, stop and report:
> FAIL — Test suite has failures. Invoke the debug-detective agent:
> "Tests are failing before my commit — [failing test name]."

On PASS, confirm the test count. If the count is LOWER than 362, report:
> WARN — Test count decreased (expected >= 362, found N).
> New features must have corresponding tests. Consider invoking test-writer.

Do NOT continue past a FAIL.

## Step 4 — Documentation staleness (WARN)

Identify staged source files (not tests):
```bash
git diff --staged --name-only | grep -E '^(backend|frontend)/.*\.py$' | grep -v '/tests/'
```

Check whether any mk-docs or CHANGELOG.md changes are also staged:
```bash
git diff --staged --name-only | grep -E '^(mk-docs/|CHANGELOG\.md)'
```

If source files are staged but NO docs changes are staged:
> WARN — Source files changed but no mk-docs updates staged.
> Invoke docs-writer: "Update docs for my recent changes before I commit."
> Suppress with [skip-docs] in the commit message.

This is WARN, not FAIL. The developer may proceed.

## Step 5 — PROGRESS.md (WARN)

```bash
git diff --staged --name-only | grep '^PROGRESS.md'
```

If PROGRESS.md is NOT staged:
> WARN — PROGRESS.md is not staged.

Check when it was last modified:
```bash
git log -1 --format="%ar" -- PROGRESS.md
```

If last modified more than 24 hours ago AND source files are staged:
> WARN (strong) — PROGRESS.md was last updated [time ago].
> Stale progress docs mean future sessions start blind. Update it now.

## Step 6 — Code review gate (BLOCKING for structural changes)

Check whether any of these are in the staged files:
- `backend/pipeline/state.py`
- `backend/pipeline/graph.py`
- `backend/services/llm.py`
- `pyproject.toml`
- `frontend/app.py`

If any are staged, this is a structural change. Invoke the code-reviewer agent:
> "Review my staged changes before I commit. Focus on architecture, state safety, and test coverage."

For non-structural changes, report: PASS (no structural changes detected).

## Step 7 — Final summary

Once all steps complete with PASS or WARN (no FAIL):

```
Commit-Ready Summary
────────────────────
Lint          PASS
Tests         PASS  (N tests)
Docs          [PASS / WARN]
PROGRESS.md   [PASS / WARN]
Code review   [PASS / SKIPPED]

Ready to commit. Run: cz commit
```

If any step is WARN, list the warnings again below the summary.

## Rules

- Never run `cz commit` or `git commit` yourself — the developer commits
- Steps 2 and 3 are always BLOCKING — no commit past a lint or test failure
- Steps 4 and 5 are warnings — the developer decides
- Step 6 is BLOCKING only for structural changes (files listed above)
- Do not run docs-writer or test-writer inline — only tell the developer the invocation phrase
- If the developer says "skip tests", remind them CONTRIBUTING.md requires all tests to pass
