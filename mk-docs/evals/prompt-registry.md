# Prompt Registry

The prompt registry enables versioned prompt management and A/B testing across pipeline agents. It allows you to define, store, and compare different prompt variants without modifying production code.

## How It Works

- **v1** is always loaded directly from the production prompts in `backend/prompts/`. This serves as the baseline.
- **v2 and beyond** are stored as standalone Python files in `backend/evals/prompt_registry/variants/`.
- Each variant file exports a `PROMPT` constant containing the full prompt template string.

## Directory Structure

```
backend/evals/prompt_registry/
├── __init__.py
├── loader.py              # Loads prompt variants by name
└── variants/
    ├── __init__.py
    ├── generate_v2.py     # Generate agent v2 prompt
    └── video_v2.py        # Video script agent v2 prompt
```

## Current Variants

### v1 (Production Baseline)

Loaded from `backend/prompts/generate.py` and `backend/prompts/video.py`. These are the prompts actively used in production.

### v2 (Optimized)

Stored in the variants directory. Key improvements over v1:

| Change | Impact |
|--------|--------|
| Added mandatory `(Curriculum)` / `(Gap)` tags | Clearer content categorization |
| Enforced script length limits (300-750 words) | Consistent video duration |
| Required contractions in scripts | More natural spoken-word tone |
| Added explicit section ordering instructions | Better structural consistency |
| Refined pedagogical depth prompting | Richer teaching content |

### v1 vs v2 Results

| Metric | v1 | v2 | Delta |
|--------|-----|-----|-------|
| **Aggregate Score** | 4.64 | 4.94 | **+0.30** |
| Domain Scope Fidelity | 4.8 | 5.0 | +0.2 |
| Gap Identification Accuracy | 4.4 | 4.8 | +0.4 |
| Curriculum Gap Separation | 4.2 | 4.8 | +0.6 |
| Pedagogical Depth | 4.6 | 5.0 | +0.4 |
| Spoken-Word Quality | 4.8 | 5.0 | +0.2 |

## Creating a New Variant

### Step 1: Create the Variant File

Create a new file in `backend/evals/prompt_registry/variants/` following the naming convention `{agent}_{version}.py`:

```python
# backend/evals/prompt_registry/variants/generate_v3.py

PROMPT = """
You are an expert educational content creator...

{your_full_prompt_template_here}
"""
```

### Step 2: Verify the Variant Loads

```bash
python -m backend.evals.cli list
```

The new variant should appear in the output.

### Step 3: Run A/B Comparison

```bash
# Compare your new variant against v2
python -m backend.evals.cli compare \
    --dataset cs224n \
    --variant-a v2 \
    --variant-b v3 \
    --verbose
```

### Step 4: Review Results

The comparison output shows:

- Aggregate score for each variant
- Per-criterion score deltas
- Statistical significance (p-value)
- Winner declaration

### Step 5: Promote to Production

If your variant wins, update the production prompts in `backend/prompts/` with the new prompt content:

1. Copy the prompt content from your variant file
2. Update `backend/prompts/generate.py` or `backend/prompts/video.py`
3. Run the full test suite to verify nothing breaks
4. The old production prompts become the new v1 baseline

!!! warning
    Always run the full eval suite before promoting a variant to production. A single dataset may not capture all edge cases.

## Variant File Requirements

Each variant file must:

- Be placed in `backend/evals/prompt_registry/variants/`
- Follow the naming convention `{agent}_{version}.py` (e.g., `generate_v3.py`, `video_v3.py`)
- Export a `PROMPT` constant at module level
- Contain the complete prompt template (no imports from other variants)

!!! tip
    Keep variant files self-contained. This makes it easy to review exactly what changed between versions and ensures reproducible evaluations.
