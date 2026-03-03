# Agentic Claude Code Setup Package

A complete file package for setting up best-practice agentic AI coding workflows with Claude Code.

## Files in This Package

| File | Purpose | Edit? |
|------|---------|-------|
| `AGENTS.md` | Universal agent memory — read by Claude Code, Cursor, Copilot, Windsurf | ✅ Fill in your project details |
| `CLAUDE.md` | Claude-specific memory with @imports | ✅ Light edits only |
| `CLAUDE.local.md` | Your personal machine overrides | ✅ Add your local URLs/data |
| `PROGRESS.md` | Cross-session state — agent updates this | ✅ Initialise with current state |
| `scripts/init.sh` | Session smoke test | ✅ Configure for your stack |
| `.claude/skills/session-handoff/SKILL.md` | Session state skill | ⚡ Ready to use |
| `docs/adr/ADR-000-template.md` | Architecture Decision Record template | 📋 Copy to create new ADRs |
| `docs/research/RESEARCH-TEMPLATE.md` | Implementation research note template | 📋 Copy to create new research notes |
| `agentic-best-practices-research-prompt.md` | Full research prompt to generate the complete guide | 🔬 Run in Claude |

## Quick Start

```bash
# 1. Copy all files into your project root
cp -r agentic-claude-code-setup/* your-project/

# 2. Fill in AGENTS.md with your project details
code AGENTS.md

# 3. Make init.sh executable and configure it
chmod +x scripts/init.sh
# Edit scripts/init.sh to use your actual commands

# 4. Gitignore CLAUDE.local.md
echo "CLAUDE.local.md" >> .gitignore

# 5. Set up symlinks for other tools (optional)
mkdir -p .cursor/rules
ln -sfn ../../AGENTS.md .cursor/rules/main.mdc
ln -sfn AGENTS.md .github/copilot-instructions.md

# 6. Open Claude Code and verify
claude
# Then type: "Read AGENTS.md and PROGRESS.md and orient yourself. Then run ./scripts/init.sh."
```

## Session Workflow

**Start every session with:**
```
Read PROGRESS.md, then run ./scripts/init.sh and report any failures.
```

**End every session with:**
```
Use the session-handoff skill to update PROGRESS.md.
```

**Before implementing anything using an external library:**
```
Check docs/research/ for existing notes, or create a new research note using RESEARCH-TEMPLATE.md before writing any code.
```

**Before making architectural decisions:**
```
Check docs/adr/ for relevant prior decisions.
```

## Generating the Full Best Practices Guide

Run `agentic-best-practices-research-prompt.md` as a prompt in Claude to generate a complete MkDocs-compatible guide. It will produce documentation that integrates directly with the file structure above.
