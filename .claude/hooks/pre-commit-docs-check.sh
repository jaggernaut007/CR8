#!/usr/bin/env bash
# .claude/hooks/pre-commit-docs-check.sh
# ─────────────────────────────────────────────────────────────────────────────
# Docs staleness check — runs before every git commit.
# Warns (does NOT block) when backend/frontend Python files are staged
# without any corresponding mk-docs/ changes.
#
# To suppress this warning for a specific commit, add [skip-docs] anywhere
# in the commit message.
# ─────────────────────────────────────────────────────────────────────────────

set -e

STAGED_BACKEND=$(git diff --staged --name-only 2>/dev/null | grep -E '^(backend|frontend)/.*\.py$' | grep -v '/tests/' || true)
STAGED_DOCS=$(git diff --staged --name-only 2>/dev/null | grep '^mk-docs/' || true)
STAGED_CHANGELOG=$(git diff --staged --name-only 2>/dev/null | grep '^CHANGELOG.md' || true)

if [ -n "$STAGED_BACKEND" ] && [ -z "$STAGED_DOCS" ] && [ -z "$STAGED_CHANGELOG" ]; then
  echo ""
  echo "⚠️  Docs check: backend/frontend files staged but no mk-docs/ or CHANGELOG.md changes."
  echo "   Changed source files:"
  echo "$STAGED_BACKEND" | sed 's/^/     /'
  echo ""
  echo "   Consider running the docs-writer agent before committing:"
  echo "   > Update the docs for my recent changes before I commit."
  echo ""
  echo "   To skip this warning: add [skip-docs] to your commit message."
  echo ""
fi

exit 0
