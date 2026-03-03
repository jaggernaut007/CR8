---
name: coverage-report
description: Run pytest with coverage analysis to find untested or under-tested modules. Produces a ranked shortlist of files below 80% and routes the weakest file to the test-writer agent. Triggers on "coverage report", "what's my coverage", "find untested files", "where is coverage weak", "missing test coverage".
---

# Coverage Report Skill

Measures test coverage for the CR8 pipeline, identifies modules below the
80% threshold, and routes the weakest file to the test-writer agent.

## Step 1 — Check pytest-cov is installed

```bash
python -c "import pytest_cov" 2>/dev/null && echo "OK" || echo "MISSING"
```

If MISSING, stop and tell the developer:
> pytest-cov is not installed. Run `make install` — it is listed in dev dependencies.

Do NOT install it yourself.

## Step 2 — Run coverage

```bash
pytest --cov=backend --cov=frontend \
       --cov-report=term-missing:skip-covered \
       -q --tb=no
```

Read the full output. If any tests FAIL, stop and report:
> Test suite has failures. Fix with the debug-detective agent before measuring coverage.

Capture the per-file coverage percentages and missing line ranges.

## Step 3 — Build the shortlist

From the coverage output, extract files that meet ALL of:
- Coverage percentage below 80%
- Path starts with `backend/` or `frontend/`
- Path does NOT contain `/tests/`
- Path does NOT start with `backend/evals/`
- Path does NOT start with `backend/prompts/`
- File is not a bare `__init__.py` (unless it contains logic)

Sort ascending by coverage percentage (lowest first).

## Step 4 — Report

Present the shortlist:

```
Coverage Report — files below 80%
──────────────────────────────────
[XX%]  backend/services/video_builder.py    (lines N-M, X-Y missing)
[XX%]  backend/pipeline/agent_research.py   (lines N-M missing)
...

Total: N files below threshold. Highest priority: [lowest file]
```

If no files are below 80%:
```
All tracked modules are at or above 80% coverage.
```
Then stop — do not invoke test-writer.

## Step 5 — Route to test-writer

For the single lowest-coverage file, report:

> Routing test-writer to `[file_path]` ([XX%] coverage).
> Uncovered lines: [line ranges from term-missing output]

Then invoke the test-writer agent:
> "Write tests for `[file_path]`. Focus on the uncovered lines: [line ranges].
> Read conftest.py first to use existing fixtures."

If more than 5 files are below threshold, report the top 3 and ask the developer
which to address first — do not queue all of them.

## Rules

- Never modify source or test files yourself — measurement and routing only
- Never run pytest-cov without confirming it is installed (Step 1)
- If the test suite has failures, stop immediately — coverage on a broken suite is meaningless
- The 80% threshold is a guideline, not a hard gate — report the data, let the developer prioritise
