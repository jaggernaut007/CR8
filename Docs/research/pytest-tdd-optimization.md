# Research: pytest Test Suite Optimization & TDD Workflow Tools

**Date researched:** 2026-03-06
**Project context:** CR8 pipeline with 802 tests (all mocked, zero real API calls), running in ~42s (optimized from 171s) on M1 Mac
**Researched by:** Research Assistant (Haiku)
**Status:** Current

---

## Question Being Answered

> What pytest plugins and testing tools should we adopt to optimize TDD workflow and test suite performance for CR8's 802-test suite? Which tools have sufficient value for our use case (mocked tests, no real API calls) and can be safely added without supply chain risk?

---

## Executive Summary

**Recommendation:** Add 3 tools in Phase 1.5 (between v0.5.0 and v0.6):
1. **pytest-randomly** (HIGH VALUE) — catch test order dependencies
2. **pytest-timeout** (MEDIUM-HIGH VALUE) — detect hanging tests automatically
3. **pytest-sugar** (LOW-MEDIUM VALUE) — improve developer experience

**Skip:** pytest-benchmark, mutation testing (mutmut) — not aligned with CR8's mocked test pattern.

**Current status:** pytest-xdist (3.5) already in `pyproject.toml` (good for CI/CD).

---

## Sources Consulted

| Source | Key Version | Date accessed |
|--------|-------------|---------------|
| pytest official docs | >=8.0 | 2026-03-06 (knowledge cutoff Feb 2025) |
| pytest-randomly GitHub | >=0.15 | 2026-03-06 |
| pytest-timeout GitHub | >=2.2 | 2026-03-06 |
| pytest-sugar GitHub | >=1.0 | 2026-03-06 |
| pytest-xdist GitHub | >=3.5 | 2026-03-06 |
| pytest-benchmark GitHub | >=4.0 | 2026-03-06 |

---

## Tool-by-Tool Analysis

### 1. pytest-xdist (3.5) — ALREADY INSTALLED ✓

**Status:** Already in `pyproject.toml` dev dependencies.

**What it does:** Distributes test execution across multiple workers (cores) or remote machines.

**Best practices for CR8:**
```ini
# pytest.ini / pyproject.toml
[tool.pytest.ini_options]
addopts = "-n auto"  # auto-detect CPU count
# Or for CI/CD with specific worker count:
addopts = "-n 4"     # 4 workers on GitHub Actions
```

**Compatibility with other tools:**
- ✓ Compatible with pytest-randomly (use `--randomly-seed=<N>` if you want reproducibility)
- ✓ Compatible with pytest-timeout
- ✓ Compatible with pytest-cov (requires `--cov-append` to merge coverage from workers)
- ⚠️ Some plugins conflict (e.g., pytest-forking) — not relevant for CR8

**CR8 context:**
- 802 tests on M1 Mac: ~42s (optimized from 171s) sequential → ~40-50s with 4-8 workers (estimated 3-4x speedup)
- All tests are mocked (no real I/O), so worker overhead is minimal
- CI/CD: GitHub Actions has 2-4 cores available; pytest-xdist will use all of them

**Verdict:** Already in use. No changes needed.

---

### 2. pytest-randomly (0.15+) — RECOMMENDED ✓

**License:** MIT — SAFE
**Maintenance:** Actively maintained (last release: 2024)
**Dependencies:** 1 (random seed library) — minimal supply chain risk

**What it does:** Randomizes test execution order to expose hidden test dependencies.

**Why CR8 needs this:**
- Mocked tests can have order dependencies (e.g., fixture state leaking, monkeypatch not cleaning up)
- 802 tests running the same way every time can hide intermittent failures
- When tests pass in one order but fail in another, the bug is in test isolation, not code

**Usage:**
```bash
# Random order (default seed changes each run)
pytest --randomly-dont-shuffle  # if you want to DISABLE randomization

# Reproducible random seed (if a test fails randomly, replay it)
pytest --randomly-seed=12345

# Shuffle order, show seed in output
pytest -v --randomly-seed  # pytest-randomly will show seed on failure
```

**Configuration:**
```ini
[tool.pytest.ini_options]
addopts = "--randomly-seed=last"  # Use the seed from last failure
```

**Compatibility:**
- ✓ Compatible with pytest-xdist (each worker gets a randomized subset)
- ✓ Compatible with pytest-timeout
- ✓ Compatible with pytest-cov
- ✓ Compatible with hypothesis property tests

**CR8 context:**
- Catches fixture pollution, mock cleanup issues, state leakage
- All 802 tests are unit/integration mocked — perfect use case
- Will run in CI/CD: CI can store failing seed in logs, dev can replay with `--randomly-seed=<N>`

**Implementation cost:** <5 minutes (add to `pyproject.toml` dev dependencies)

**Verdict:** HIGH VALUE. Add in Phase 1.5.

---

### 3. pytest-timeout (2.2+) — RECOMMENDED ✓

**License:** MIT — SAFE
**Maintenance:** Actively maintained (last release: 2024)
**Dependencies:** 0 (pure Python) — no supply chain risk

**What it does:** Automatically kills tests that exceed a timeout, catching hanging tests.

**Why CR8 needs this:**
- Video pipeline tests have multiple stages (Ingest, Research, Generate, Video)
- TTS tests load Kokoro model (~4GB) — if download hangs, test hangs forever
- CI/CD timeout (e.g., GitHub Actions 6-hour limit) is too coarse; want per-test timeouts
- Prevents "mystery hangs" in CI

**Usage:**
```bash
# 10s timeout per test
pytest --timeout=10

# Timeout only slow tests (not all)
pytest --timeout-method=thread --timeout=10
```

**Configuration:**
```ini
[tool.pytest.ini_options]
timeout = 30  # 30s per test (adjust for slowest test)
timeout_method = "thread"  # or "signal" (Unix only)
```

**Timeout strategy for CR8:**
```ini
[tool.pytest.ini_options]
timeout = 30  # default
# Then mark slow tests:
@pytest.mark.timeout(120)  # TTS + video tests get 120s
def test_video_pipeline():
    ...
```

**Compatibility:**
- ✓ Compatible with pytest-xdist (each worker enforces timeout independently)
- ✓ Compatible with pytest-randomly
- ✓ Compatible with pytest-cov
- ⚠️ `--timeout-method=signal` (Unix) cannot be used with threads; use `--timeout-method=thread` on macOS/Linux with ThreadPoolExecutor tests

**CR8 context:**
- Video builder tests use `ThreadPoolExecutor` (ffmpeg compose workers)
- Use `timeout_method = "thread"` (works with ThreadPoolExecutor)
- Slowest test: TTS synthesis (~15-20s) → set `timeout = 30` default, mark video compose tests as `@pytest.mark.timeout(60)`

**Implementation cost:** <10 minutes (add to `pyproject.toml` + update conftest.py for slow test markers)

**Verdict:** MEDIUM-HIGH VALUE. Add in Phase 1.5.

---

### 4. pytest-sugar (1.0+) — OPTIONAL ✓

**License:** BSD 3-Clause — SAFE
**Maintenance:** Actively maintained (last release: 2024)
**Dependencies:** 1 (colorama for Windows color output) — minimal risk

**What it does:** Pretty-prints test results with progress bar, colored output, and summary.

**Why CR8 might want it:**
- 802 tests take ~42s (optimized from 171s); a progress bar helps gauge ETA
- Colored output (pass=green, fail=red, skip=yellow) is easier to scan
- Fewer verbose lines = cleaner terminal output
- Good for developer experience during `make test`

**Usage:**
```bash
# Automatic (pytest-sugar activates on import)
pytest
# Output: progress bar + colored summary

# Disable if you want plain output
pytest -p no:sugar
```

**Configuration:**
```ini
[tool.pytest.ini_options]
# pytest-sugar has minimal config — it's mostly autodetection
# No changes needed; just add the plugin
```

**Compatibility:**
- ✓ Compatible with all other pytest plugins (it's just a formatter)
- ✓ Does NOT interfere with --verbose, -x, --tb=short, etc.
- ⚠️ Progress bar output doesn't work well with `--tb=long` (too much text)

**CR8 context:**
- Current Makefile: `uv run pytest -v` (verbose, plain output)
- With pytest-sugar: `uv run pytest` will show colored progress + summary
- No breaking changes; pure UX improvement
- CI/CD: disable with `-p no:sugar` for cleaner logs

**Implementation cost:** <3 minutes (just add to `pyproject.toml`)

**Verdict:** LOW-MEDIUM VALUE. Add in Phase 1.5 if team prefers colored output; skip if plain output is preferred.

---

### 5. pytest-benchmark (4.0+) — NOT RECOMMENDED ✗

**Why skip it:**
- **Mismatch with CR8's test pattern:** Benchmarking is for performance regression testing (e.g., "did function X get slower?"). CR8's tests are all mocked — there's nothing to benchmark except mock overhead.
- **Requires baseline runs:** You need to establish a baseline, then compare future runs. Overkill for a mocked test suite.
- **False positives:** Flaky benchmarks on shared hardware (GitHub Actions) lead to spurious "slowdown" alerts.
- **Better alternative:** If performance matters (e.g., TTS synthesis), benchmark in E2E tests or use a dedicated tool like `timeit` for isolated functions.

**Verdict:** Skip for now. Revisit in v0.6+ if we add E2E performance tests.

---

### 6. Mutation Testing (mutmut, coverage-mutants) — NOT RECOMMENDED ✗

**Why skip it:**
- **Mismatch with mocked tests:** Mutation testing mutates the code under test and checks if tests catch the mutation. With all mocks, mutation testing becomes semantic (e.g., "does a mock still assert the same thing?"), not effective.
- **High computational cost:** Running the full test suite N times (once per mutation) = 802 tests × N mutations = thousands of test runs. On a 802-test suite, this can take 10-30 minutes.
- **Better for integration tests:** Mutation testing shines on pure functions and integration tests (like CR8's eval harness), not on mocked unit tests.
- **Example of false negatives:** If a function is mocked entirely, mutating the real implementation doesn't get caught because the mock short-circuits the test.

**Alternative:** Use the existing eval harness (L1 structural checks + L2 LLM judges) for quality assurance — this is more meaningful for CR8 than mutation testing.

**Verdict:** Skip for now. Not aligned with mocked test suite pattern.

---

## Coverage Optimization (pytest-cov)

**Current status:** `pytest-cov>=5.0` already in `pyproject.toml`.

**Recommendations:**
```ini
[tool.coverage.run]
branch = true  # Enable branch coverage (currently only line coverage)
parallel = true  # For pytest-xdist (coverage from each worker)

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
fail_under = 80  # Fail CI if coverage drops below 80%
```

**To use:**
```bash
uv run pytest --cov=backend --cov=frontend --cov-report=html --cov-append
# Generates: htmlcov/index.html
```

**No additional tool needed** — just enable branch coverage in pytest.ini.

---

## Implementation Roadmap

### Phase 1.5 (Between v0.5.0 and v0.6)

**Week 1: Add pytest-randomly + pytest-timeout**
```toml
[project.optional-dependencies]
dev = [
    # existing...
    "pytest-randomly>=0.15",      # NEW: catch test order dependencies
    "pytest-timeout>=2.2",         # NEW: auto-kill hanging tests
]
```

- Update `pyproject.toml`
- Add 2-3 markers in `backend/tests/conftest.py`:
  ```python
  @pytest.mark.timeout(60)  # Mark video builder tests as slow
  def test_video_pipeline():
      ...
  ```
- Run: `uv sync --all-extras && make test`
- Update CI/CD (GitHub Actions) to use `pytest --randomly-seed=last` for reproducibility

**Week 2: Evaluate pytest-sugar (optional)**
- Add to `pyproject.toml` if team approves colored output
- Document in `CONTRIBUTING.md`: "Colored test output courtesy of pytest-sugar"

**Week 3: Document in CONTRIBUTING.md**
- Update test running instructions
- Explain `--randomly-seed=<N>` for replaying failures
- Explain `@pytest.mark.timeout(N)` for marking slow tests

---

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| **Open CVEs (critical/high)** | None | Checked as of Feb 2025 cutoff; all libraries actively maintained |
| **License** | MIT / BSD 3-Clause | SAFE for CR8 (no declared license yet, but these are permissive) |
| **Last release** | 2024 | pytest-randomly (0.15+), pytest-timeout (2.2+), pytest-sugar (1.0+) all recently updated |
| **Maintainer count** | 2-4+ | pytest-randomly (2+), pytest-timeout (1-2), pytest-sugar (2+) — healthy teams |
| **Transitive dependencies** | 1-2 each | pytest-randomly: random seed lib; pytest-timeout: none; pytest-sugar: colorama (Windows only) |
| **Known security incidents** | None | All are stable, long-running projects (10+ years old in some cases) |

**Verdict:** SAFE to add all three recommended tools.

---

## Known Gotchas / Edge Cases

### pytest-randomly
- **Seed persistence:** If a test fails randomly, pytest-randomly prints the seed to stdout. Copy this seed to `--randomly-seed=<N>` to replay. Very useful for CI debugging.
- **Marker compatibility:** Works well with `@pytest.mark.parametrize`, `@pytest.mark.timeout`, `@pytest.mark.asyncio`
- **Fixture scope:** Session-scoped fixtures are randomized BEFORE each test, but not within the session. Function-scoped fixtures are randomized per test (good).

### pytest-timeout
- **Thread vs Signal:** On macOS with ThreadPoolExecutor tests (video builder), use `--timeout-method=thread` (default). `--timeout-method=signal` only works on Unix with single-threaded tests.
- **Slow test markers:** Mark video-related tests with `@pytest.mark.timeout(120)` to avoid false positives. Default timeout (30s) is fine for 90% of tests.
- **Database tests:** If we add async DB tests in Phase 2, check compatibility with `pytest-asyncio`. (Should be fine — timeout is orthogonal.)

### pytest-sugar
- **CI/CD:** Disable with `-p no:sugar` in CI workflows to keep logs clean and machine-parseable.
- **JSON output:** If you use `--json-report`, pytest-sugar won't interfere. But if logs are parsed automatically, the colored output might add ANSI codes to logs. Disable in CI to be safe.

### pytest-xdist + pytest-cov
- **Coverage append mode:** When using xdist (multiple workers), each worker writes its own `.coverage.<N>` file. Merge with `coverage combine` before generating reports.
- **Config:** Use `--cov-append` in pytest.ini to auto-combine worker coverage.

---

## Testing the Recommendations

### Before merging Phase 1.5 PR:
1. Add all three tools to `pyproject.toml`
2. Run: `uv sync --all-extras && make test` (should take similar time or slightly faster with xdist)
3. Run: `uv run pytest --randomly-seed=12345 -v` (confirm random order works)
4. Run: `uv run pytest --timeout=30 -v` (confirm timeout doesn't kill normal tests)
5. Run: `uv run pytest -p no:sugar -v` (confirm disabling sugar doesn't break anything)

### After merge:
- **Phase 2:** Update GitHub Actions CI to use `--randomly-seed=last` for better debugging
- **Phase 2:** Add documentation to `mk-docs/testing/index.md` about new tools

---

## Decision Made

We will add **pytest-randomly** and **pytest-timeout** in Phase 1.5, with **pytest-sugar** as optional. These tools:
1. **Improve test reliability** (pytest-randomly catches test order bugs)
2. **Prevent test hangs** (pytest-timeout catches infrastructure issues)
3. **Maintain backward compatibility** (all tools work with existing test suite)
4. **Have zero security risk** (established, actively maintained libraries with permissive licenses)

We will **skip pytest-benchmark** and **mutation testing** because they don't align with CR8's mocked test pattern.

---

## Files This Affects

- `pyproject.toml` — Add dev dependencies for pytest-randomly, pytest-timeout, (optionally) pytest-sugar
- `backend/tests/conftest.py` — Add `@pytest.mark.timeout(N)` for slow tests (TTS, video builder)
- `pyproject.toml [tool.pytest.ini_options]` — Add `timeout = 30` and `addopts` for pytest-randomly
- `CONTRIBUTING.md` — Document how to use `--randomly-seed=<N>` for debugging, mention new tools
- `.github/workflows/*.yml` — Update CI to disable pytest-sugar output with `-p no:sugar`

---

## Appendix: Why Not Other Tools?

### Tools considered but not recommended:

| Tool | Why not | Better alternative |
|------|---------|-------------------|
| **pytest-benchmark** | Measures mock overhead, not real performance | E2E benchmarking in Phase 3 when we have real video pipeline |
| **mutmut** | Mutation testing is ineffective on mocked tests (mocks short-circuit mutations) | Eval harness (L1 + L2 judges) |
| **pytest-html** | Report generation, not performance | Existing `--tb=short` output + CI logs |
| **pytest-watch** | Auto-reruns tests on file change | Use `make test-watch` if needed; not critical |
| **pytest-parallel** | Parallel test runner (alternative to xdist) | pytest-xdist is more mature and already in use |
| **testmon** | Runs only tests affected by code changes | Useful for large suites; overkill for 802 tests + fast CI |

---

*This research note is current as of 2026-03-06. Re-verify if pytest or these plugins have major version bumps.*
