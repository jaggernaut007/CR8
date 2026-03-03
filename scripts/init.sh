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

# ── 2. Dependency check ──────────────────────────────────────────────────────
echo ""
echo "▶ Checking dependencies..."
if python3 -c "import fastapi, langgraph, chromadb" 2>/dev/null; then
  echo "  ✓ Core dependencies installed"
else
  echo "  ✗ Missing dependencies — run: make install"
  exit 1
fi

# ── 2b. Commitizen check ─────────────────────────────────────────────────────
echo ""
echo "▶ Checking commitizen..."
if command -v cz &>/dev/null; then
  echo "  ✓ Commitizen installed ($(cz version 2>/dev/null | head -1))"
else
  echo "  ⚠ Commitizen not found — run: make install"
fi

# ── 3. Linter check ─────────────────────────────────────────────────────────
echo ""
echo "▶ Running Ruff linter..."
if ruff check . --quiet; then
  echo "  ✓ Ruff: no issues"
else
  echo "  ✗ Ruff found issues — run: make lint-fix"
  exit 1
fi

# ── 4. Test suite ────────────────────────────────────────────────────────────
echo ""
echo "▶ Running test suite (362 tests)..."
pytest -q --tb=short
echo "  ✓ All tests passing"

# ── 5. Docs build check ──────────────────────────────────────────────────────
echo ""
echo "▶ Checking MkDocs build..."
if mkdocs build --strict --quiet 2>/dev/null; then
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
