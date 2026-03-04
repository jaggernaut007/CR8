# CR8 Evaluation Framework

Two-layer evaluation system for validating pipeline output quality.

## Layers

- **L1 (Structural)**: 20+ automated checks — section counts, word counts, formatting, JSON schema compliance. Fast, deterministic, zero API cost.
- **L2 (LLM Judge)**: DeepSeek-V3 evaluates content quality against rubrics (accuracy, depth, relevance, pedagogical value). Requires `DEEPSEEK_API_KEY`.

## Usage

```bash
# Run evals on the cs224n dataset
python -m backend.evals run --dataset cs224n

# A/B comparison between prompt variants
python -m backend.evals compare --baseline v1 --candidate v2 --dataset cs224n
```

## Directory Structure

- `datasets/` — Test datasets (input PDFs + expected outputs)
- `harness/` — Runner, scorer, result models
- `judges/` — L2 LLM judge implementations
- `prompt_registry/` — Versioned prompt variants for A/B testing
- `structural/` — L1 structural check implementations
- `reports/` — Generated eval reports (gitignored)

## Adding a New Judge

1. Create a new class in `judges/` extending `BaseJudge`
2. Define the rubric and scoring criteria
3. Register in the judge registry
4. Add corresponding L1 structural checks if applicable
