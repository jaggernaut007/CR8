#!/usr/bin/env python3
"""Sync the Claude Code skill/agent harness into Cline's skill + workflow directories.

Cline loads two kinds of reusable instructions:
  - Skills    from ``~/.cline/skills/<name>/SKILL.md``  (frontmatter: ``name`` + ``description``)
  - Workflows from ``~/Documents/Cline/Workflows/<name>.md`` (frontmatter: ``description``)

The Claude Code harness (the single source of truth for these reusable tools) lives in:
  - ``~/.claude/skills/<name>/SKILL.md``  (frontmatter: ``name`` / ``description`` / ``model``)
  - ``~/.claude/agents/<name>.md``
    (frontmatter: ``name`` / ``description`` / ``model`` / ``tools``)

Cline has no per-skill/per-agent model frontmatter — it routes model tiers through the
Plan/Act split (Plan = high-capability, Act = mid-tier). So this script drops the
Claude-only fields (``model``, ``tools``, ``disable-model-invocation``) and translates the
``model:`` tier alias into a plain-language note in the body.

Mapping:
  - Claude Code skill  -> Cline skill     (``~/.cline/skills/``)
  - Claude Code agent  -> Cline workflow  (``~/Documents/Cline/Workflows/``)

Cline's built-in *subagents* are read-only parallel-research agents that are not
user-customisable, so write-capable Claude Code agents map to workflows instead.

Usage:
    python3 scripts/sync-cline-harness.py          # add missing entries, skip existing
    python3 scripts/sync-cline-harness.py --force  # overwrite everything from source
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HOME = Path.home()
CLAUDE_SKILLS = HOME / ".claude" / "skills"
CLAUDE_AGENTS = HOME / ".claude" / "agents"
CLINE_SKILLS = HOME / ".cline" / "skills"
CLINE_WORKFLOWS = HOME / "Documents" / "Cline" / "Workflows"

# Claude Code model-tier alias -> Cline-idiom note (Cline routes tiers via Plan/Act).
TIER_NOTE = {
    "opus": "Prefer a high-capability model tier (Plan mode) for this task.",
    "fable": "Prefer a high-capability model tier (Plan mode) for this task.",
    "sonnet": "Run on the Act-mode (mid-tier) model.",
    "haiku": "Run on a fast mechanical tier (Act mode).",
}

MAX_DESCRIPTION_LEN = 1024  # Cline enforces a 1024-char description limit.
MIN_QUOTED_SCALAR_LEN = 2  # a quoted YAML scalar needs at least an opening + closing quote


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a markdown file into its YAML frontmatter dict and the remaining body."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text

    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if len(val) >= MIN_QUOTED_SCALAR_LEN and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        meta[key] = val

    body = "\n".join(lines[end + 1 :]).strip("\n")
    return meta, body


def yaml_scalar(value: str) -> str:
    """Return ``value`` safely for a single-line YAML scalar, quoting only when needed."""
    needs_quote = (
        value != value.strip()
        or "\n" in value
        or ": " in value
        or " #" in value
        or value.startswith(
            (
                "!", "&", "*", "-", "?", "|", ">", "%", "@", "`",
                "'", '"', "{", "}", "[", "]", ",", "#",
            )
        )
        or value.lower() in ("null", "true", "false", "yes", "no", "on", "off", "~")
    )
    if not needs_quote:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def tier_note(model: str) -> str:
    """Translate a Claude Code model alias into a Cline-idiom note (empty if unknown)."""
    return TIER_NOTE.get(model.strip().lower(), "")


def build_skill(name: str, meta: dict[str, str], body: str) -> str:
    """Build a Cline SKILL.md from a Claude Code skill."""
    description = meta.get("description", "")
    model = meta.get("model", "")
    note = tier_note(model)

    if meta.get("disable-model-invocation", "").strip().lower() == "true":
        note = (note + " " if note else "") + "Invoke manually (user-timed action)."

    lines = ["---", f"name: {name}", f"description: {yaml_scalar(description)}", "---", ""]
    if body:
        lines.append(body)
    if note:
        lines.append("")
        lines.append(f"**Model tier:** {note}")
    return "\n".join(lines).rstrip() + "\n"


def build_workflow(meta: dict[str, str], body: str) -> str:
    """Build a Cline workflow .md from a Claude Code agent."""
    description = meta.get("description", "")
    model = meta.get("model", "")
    note = tier_note(model)

    lines = ["---", f"description: {yaml_scalar(description)}", "---", ""]
    if body:
        lines.append(body)
    if note:
        lines.append("")
        lines.append(f"**Model tier:** {note}")
    return "\n".join(lines).rstrip() + "\n"


def _description_warning(description: str) -> str:
    """Return the warning line when a description exceeds Cline's length cap."""
    return f"    ! description is {len(description)} chars (Cline caps at {MAX_DESCRIPTION_LEN})"


def _sync_one_skill(src_dir: Path, name: str, force: bool) -> list[str]:
    """Convert one Claude Code skill into a Cline skill. Returns report lines."""
    report: list[str] = []
    src = src_dir / "SKILL.md"
    if not src.is_file():
        return report

    meta, body = parse_frontmatter(src.read_text(encoding="utf-8"))
    description = meta.get("description", "")

    dest_dir = CLINE_SKILLS / name
    dest = dest_dir / "SKILL.md"
    action = "created"
    if dest.exists() and not force:
        action = "skipped"
    elif dest.exists():
        action = "overwritten"

    report.append(f"  skill     {name:<20} -> {dest} ({action})")
    if action == "skipped":
        return report

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(build_skill(name, meta, body), encoding="utf-8")

    if len(description) > MAX_DESCRIPTION_LEN:
        report.append(_description_warning(description))

    return report


def sync_skills(force: bool) -> list[str]:
    """Convert every Claude Code skill into a Cline skill. Returns report lines."""
    report: list[str] = []
    if not CLAUDE_SKILLS.is_dir():
        report.append(f"  (no skills source at {CLAUDE_SKILLS})")
        return report

    for src_dir in sorted(CLAUDE_SKILLS.iterdir()):
        if not src_dir.is_dir():
            continue
        report.extend(_sync_one_skill(src_dir, src_dir.name, force))

    return report


def sync_agents(force: bool) -> list[str]:
    """Convert every Claude Code agent into a Cline workflow. Returns report lines."""
    report: list[str] = []
    if not CLAUDE_AGENTS.is_dir():
        report.append(f"  (no agents source at {CLAUDE_AGENTS})")
        return report

    for src in sorted(CLAUDE_AGENTS.glob("*.md")):
        meta, body = parse_frontmatter(src.read_text(encoding="utf-8"))
        name = src.stem
        description = meta.get("description", "")

        dest = CLINE_WORKFLOWS / f"{name}.md"
        action = "created"
        if dest.exists() and not force:
            action = "skipped"
        elif dest.exists():
            action = "overwritten"

        report.append(f"  workflow {name:<20} -> {dest} ({action})")
        if action == "skipped":
            continue

        CLINE_WORKFLOWS.mkdir(parents=True, exist_ok=True)
        dest.write_text(build_workflow(meta, body), encoding="utf-8")

        if len(description) > MAX_DESCRIPTION_LEN:
            report.append(_description_warning(description))

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing Cline skills/workflows (default: skip to preserve hand tweaks)",
    )
    args = parser.parse_args()

    print("Syncing Claude Code harness -> Cline:")
    print(f"  skills source : {CLAUDE_SKILLS}")
    print(f"  agents source : {CLAUDE_AGENTS}")
    print(f"  skills target : {CLINE_SKILLS}")
    print(f"  workflows     : {CLINE_WORKFLOWS}")
    print()

    print("Skills:")
    print("\n".join(sync_skills(args.force)))
    print()
    print("Agents -> workflows:")
    print("\n".join(sync_agents(args.force)))
    print()
    print("Done. Re-run with --force to overwrite existing entries from source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
