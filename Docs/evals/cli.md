# CLI Reference

The eval CLI provides commands for running structural checks, full evaluations, and A/B comparisons.

**Entry point**: `python -m backend.evals.cli`

## Commands

### `check` -- Structural Checks Only (L1)

Run free, instant structural checks on cached pipeline outputs.

```bash
python -m backend.evals.cli check --dataset <dataset_id>
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dataset` | *required* | Dataset ID (e.g., `cs224n`) |
| `--output-type` | `all` | Filter by output type: `module`, `ppt`, `script`, or `all` |
| `--topic` | `None` | Run checks for a specific topic only |
| `--verbose` | `False` | Show detailed check results including pass/fail messages |
| `--json` | `False` | Output results as JSON |

**Example**:

```bash
# Check all outputs for cs224n dataset
python -m backend.evals.cli check --dataset cs224n

# Check only module outputs with verbose output
python -m backend.evals.cli check --dataset cs224n --output-type module --verbose

# Check a specific topic
python -m backend.evals.cli check --dataset cs224n --topic "attention_mechanisms"
```

### `run` -- Full Evaluation (L1 + L2)

Run both structural checks and LLM judge evaluation.

```bash
python -m backend.evals.cli run --dataset <dataset_id> --variant <variant>
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dataset` | *required* | Dataset ID (e.g., `cs224n`) |
| `--variant` | *required* | Prompt variant to evaluate (e.g., `v1`, `v2`) |
| `--output-type` | `all` | Filter by output type: `module`, `ppt`, `script`, or `all` |
| `--topic` | `None` | Evaluate a specific topic only |
| `--skip-structural` | `False` | Skip L1 checks, run L2 judge only |
| `--verbose` | `False` | Show detailed scoring breakdown |
| `--json` | `False` | Output results as JSON |

**Example**:

```bash
# Full eval of v1 prompts on cs224n
python -m backend.evals.cli run --dataset cs224n --variant v1

# Evaluate only scripts with v2 prompts
python -m backend.evals.cli run --dataset cs224n --variant v2 --output-type script

# JSON output for programmatic use
python -m backend.evals.cli run --dataset cs224n --variant v2 --json
```

!!! note
    The `run` command requires a `DEEPSEEK_API_KEY` environment variable and costs approximately $0.02 per evaluation run.

### `compare` -- A/B Comparison

Compare two prompt variants side-by-side with statistical significance testing.

```bash
python -m backend.evals.cli compare --dataset <dataset_id> --variant-a <a> --variant-b <b>
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dataset` | *required* | Dataset ID (e.g., `cs224n`) |
| `--variant-a` | *required* | First prompt variant (e.g., `v1`) |
| `--variant-b` | *required* | Second prompt variant (e.g., `v2`) |
| `--output-type` | `all` | Filter by output type |
| `--verbose` | `False` | Show per-criterion score deltas |
| `--json` | `False` | Output results as JSON |

**Example**:

```bash
# Compare v1 vs v2 on cs224n
python -m backend.evals.cli compare --dataset cs224n --variant-a v1 --variant-b v2

# Compare with detailed per-criterion breakdown
python -m backend.evals.cli compare --dataset cs224n --variant-a v1 --variant-b v2 --verbose
```

### `list` -- List Available Resources

List available datasets, variants, and cached results.

```bash
python -m backend.evals.cli list
```

**Example output**:

```
Datasets:
  cs224n    5 topics, cached_state available

Variants:
  v1        Production prompts (backend/prompts/)
  v2        generate_v2.py, video_v2.py

Cached Results:
  cs224n/v1  5 topics evaluated (2024-01-15)
  cs224n/v2  5 topics evaluated (2024-01-16)
```

## A/B Comparison Workflow

For a complete A/B comparison using the dedicated runner:

```bash
# Run full A/B comparison (generates outputs, evaluates, compares)
python -m backend.evals.run_ab_comparison --dataset cs224n --topics 5
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dataset` | *required* | Dataset ID |
| `--topics` | `all` | Number of topics to evaluate |
| `--variant-a` | `v1` | First variant |
| `--variant-b` | `v2` | Second variant |
| `--skip-generation` | `False` | Skip output generation, use cached outputs |

This runner orchestrates the full workflow:

1. Loads the dataset manifest
2. Runs the pipeline with variant A prompts
3. Runs the pipeline with variant B prompts
4. Evaluates both sets of outputs (L1 + L2)
5. Computes comparison statistics and declares a winner

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | -- | DeepSeek API key for L2 judge (required for `run` and `compare`) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API endpoint |

!!! tip
    Set `PYTHONUNBUFFERED=1` when running eval scripts to see output in real-time, and `TOKENIZERS_PARALLELISM=false` to suppress HuggingFace warnings.
