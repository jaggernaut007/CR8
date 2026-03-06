# Evaluation Framework

CR8 includes a two-layer evaluation system for measuring and comparing prompt quality across pipeline outputs. Located in `backend/evals/`.

## Architecture

```
L1: Structural Checks (free)     L2: LLM Judge (~$0.02/run)
├── module_checks.py (8 checks)  ├── ModuleJudge (9 criteria)
├── ppt_checks.py (5+ checks)    ├── PPTJudge (6 criteria)
└── script_checks.py (7 checks)  ├── ScriptJudge (7 criteria)
                                  └── ConsistencyJudge (cross-output)
```

**L1 (Structural)** — Free, fast checks on format and completeness: required sections present, sections in order, minimum length, Bloom's taxonomy verbs, (Curriculum)/(Gap) tags, word count ranges, no markdown in scripts, contractions used.

**L2 (LLM Judge)** — DeepSeek-V3 evaluates outputs against weighted rubrics on a 1-5 scale. Criteria include domain scope fidelity, gap identification accuracy, pedagogical depth, spoken-word quality, and cross-output consistency.

## Quick Start

```bash
# Install all dependencies (includes eval extras)
uv sync --all-extras

# L1 structural checks only (free)
python -m backend.evals.cli check --dataset cs224n

# Full eval with L2 judge (~$0.02/run)
python -m backend.evals.cli run --dataset cs224n --variant v1

# A/B comparison
python -m backend.evals.cli compare --dataset cs224n --variant-a v1 --variant-b v2
```

## Sections

- **[Architecture](architecture.md)** — L1 structural checks and L2 judge details
- **[CLI Reference](cli.md)** — All CLI commands with examples
- **[Prompt Registry](prompt-registry.md)** — Prompt versioning and A/B testing workflow
- **[Writing Custom Evals](custom-evals.md)** — How to add new checks and judges
