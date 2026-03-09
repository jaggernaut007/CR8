# ADR-009: uv Package Manager Migration (pip to uv)
<!-- Architecture Decision Record
     Place in: docs/adr/ADR-009-uv-package-manager.md
     Reference from AGENTS.md so the agent knows these exist.
     The agent reads ADRs before making structural decisions. -->

**Date:** 2026-03-06
**Status:** Accepted
**Deciders:** Shreyas Jagannath

---

## Context

CR8 used pip + venv for dependency management from v0.1 through v0.4.1. This caused
recurring friction:

- **No lockfile.** pip does not produce a lockfile. Without one, `pip install` could
  resolve to different versions on different machines or in CI. We relied on loose
  `>=` constraints in `pyproject.toml` with no mechanism to pin transitive dependencies.
- **Slow installs.** A clean `pip install` of CR8's 33 direct dependencies (plus
  transitive) took 45-90 seconds locally and longer in Docker builds.
- **Multiple tools.** Developers needed `python -m venv` to create environments,
  `pip install -e .` to install, and `python -m <tool>` to run — three separate
  invocations with no unified interface.
- **Docker layer cache misses.** Without a lockfile, any change to `pyproject.toml`
  invalidated the entire install layer, even if only metadata changed.

The v0.5.1 release (foundation phase) was the right moment to migrate because it
already touched Makefile targets, Dockerfile, CI, and all developer documentation.

## Decision

> We will use **uv** (by Astral) as the sole Python package manager, replacing pip,
> venv, and pip-tools, because it provides 10-100x faster installs, a built-in lockfile,
> and a single `uv run` command that eliminates manual venv activation.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **uv (Astral) — chosen** | 10-100x faster installs (Rust-based); built-in lockfile (`uv.lock`); single tool for venv+install+run; PEP 621 compliant (no pyproject.toml format change); `uv sync --frozen` for deterministic Docker/CI builds; official Docker image at `ghcr.io/astral-sh/uv` | Relatively new project (risk of breaking changes); team must learn new commands; not yet included in most OS package managers |
| **pip + venv (status quo)** | Universal — ships with Python; zero learning curve; massive ecosystem of tutorials | No lockfile without pip-tools; slow resolution and install; separate tools for venv/install/run; non-deterministic builds |
| **Poetry** | Mature lockfile (`poetry.lock`); good dependency resolution; large community | Non-standard `[tool.poetry]` pyproject.toml section; slower than uv; heavy runtime; would require reformatting pyproject.toml |
| **PDM** | PEP 621 compliant; built-in lockfile; good resolver | Smaller community than Poetry or uv; slower than uv; less Docker tooling and documentation |
| **pip-tools** | Adds `pip-compile` for lockfile generation; minimal change from pip workflow | Still uses pip for installs (slow); requires separate venv management; two tools instead of one; no `run` command |

## Consequences

**Positive:**
- Docker builds are deterministic: `uv sync --frozen` fails if `uv.lock` is stale
- Docker layer caching improved: `pyproject.toml` + `uv.lock` copied before source code
- Local install time dropped from ~60s to ~2s on warm cache
- `uv run <command>` replaces `source .venv/bin/activate && python -m <command>`
- `pyproject.toml` format unchanged — standard PEP 621, still uses hatchling as build backend

**Negative / Trade-offs:**
- All developers must install uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- uv is pre-1.0 — API surface may shift (mitigated by pinning uv version in Dockerfile)
- `uv.lock` adds a large file to the repo (~3000+ lines) that creates merge conflicts on dependency changes

**Neutral:**
- `uv.lock` replaces the role a `requirements.txt` would have played — same concept, better format
- Optional dependency groups (`dev`, `eval`, `docs`) work identically with `uv sync --all-extras`

## Implementation Notes

- **Files changed in migration:**
  - `pyproject.toml` — no format changes needed (already PEP 621)
  - `uv.lock` — new file, committed to repo
  - `Makefile` — all targets changed from `pip`/`python -m` to `uv sync`/`uv run`
  - `Dockerfile` — builder stage: `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`, then `uv sync --frozen --no-dev --no-editable`
  - `scripts/init.sh` — commands updated to use `uv run`
  - All documentation (CLAUDE.md, MEMORY.md, mk-docs pages, README.md) — command examples updated
- **Patterns to follow:**
  - Always use `uv run <tool>` instead of activating a venv (e.g., `uv run pytest`, `uv run ruff`)
  - Use `uv sync --all-extras` for local dev; `uv sync --frozen --no-dev` for production/Docker
  - After adding a dependency to `pyproject.toml`, run `uv sync` to regenerate `uv.lock`
  - Pin uv version in Dockerfile via the image tag (e.g., `ghcr.io/astral-sh/uv:0.10.8`)
- **Things to avoid:**
  - Never use `pip install` directly — it bypasses the lockfile
  - Never use `python -m venv` — uv manages its own `.venv` automatically
  - Never commit a stale `uv.lock` — CI should fail on `uv sync --frozen` if it is out of date
  - Do not add a `requirements.txt` — `uv.lock` is the single source of truth

## References

- [uv documentation](https://docs.astral.sh/uv/)
- [Astral (uv maintainer)](https://astral.sh/)
- Dockerfile: `COPY --from=ghcr.io/astral-sh/uv:latest` pattern
- `pyproject.toml` — PEP 621 project metadata
- `Makefile` — all `uv run` targets
