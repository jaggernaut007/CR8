#!/usr/bin/env bash
# scripts/init.sh
# ─────────────────────────────────────────────────────────────────────────────
# CR8 Session Initialisation & Smoke Test
# Run at the START of every agent session and after major changes.
# Purpose: Confirm the app is in a working state before building on it.
# The agent should fix any failures here before starting new work.
# ─────────────────────────────────────────────────────────────────────────────

set -e  # Exit immediately on any failure

echo "═══════════════════════════════════════════"
echo "  CR8 Session Init & Smoke Test"
echo "  $(date)"
echo "═══════════════════════════════════════════"

# ── 1. Environment check ──────────────────────────────────────────────────────
echo ""
echo "▶ Checking environment..."
if [ ! -f ".env" ]; then
  echo "  ⚠ WARNING: .env file not found"
  echo "    Copy .env.example → .env and add your API keys"
  echo "    (Tests will still pass — they mock all API calls)"
else
  echo "  ✓ .env file present"
fi

# ── 2. Dependency check (uv) ─────────────────────────────────────────────────
echo ""
echo "▶ Checking dependencies (uv)..."
if ! command -v uv &>/dev/null; then
  echo "  ✗ uv not found — install: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
echo "  ✓ uv $(uv --version | awk '{print $2}')"
if uv sync --check 2>/dev/null; then
  echo "  ✓ Dependencies in sync with uv.lock"
else
  echo "  ⚠ Dependencies out of sync — running: uv sync --all-extras"
  uv sync --all-extras
  echo "  ✓ Dependencies synced"
fi

# ── 2b. Commitizen check ─────────────────────────────────────────────────────
echo ""
echo "▶ Checking commitizen..."
if uv run cz version &>/dev/null; then
  echo "  ✓ Commitizen installed ($(uv run cz version 2>/dev/null | head -1))"
else
  echo "  ⚠ Commitizen not found — run: make install"
fi

# ── 3. Linter check ─────────────────────────────────────────────────────────
echo ""
echo "▶ Running Ruff linter..."
if uv run ruff check . --quiet; then
  echo "  ✓ Ruff: no issues"
else
  echo "  ✗ Ruff found issues — run: make lint-fix"
  exit 1
fi

# ── 4. Test suite ────────────────────────────────────────────────────────────
echo ""
echo "▶ Running test suite..."
uv run pytest -q --tb=short
echo "  ✓ All tests passing"

# ── 5. Docs build check ──────────────────────────────────────────────────────
echo ""
echo "▶ Checking MkDocs build..."
if uv run mkdocs build --strict --quiet 2>/dev/null; then
  echo "  ✓ Docs build clean"
else
  echo "  ⚠ Docs build has warnings (non-blocking — fix when convenient)"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ All checks passed — safe to proceed"
echo ""
echo "  📋 Read PROGRESS.md for current task state"
echo "  🔑 App runs on http://localhost:8080 (make dev)"
echo "  📚 Docs run on http://localhost:8000 (make docs-serve)"
echo "═══════════════════════════════════════════"
echo ""
