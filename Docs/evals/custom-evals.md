# Writing Custom Evals

This guide covers how to extend the evaluation framework with new structural checks, LLM judges, and datasets.

## Adding a Structural Check

Structural checks are free, instant validations that run without any API calls. They verify format, completeness, and basic quality constraints.

### Step 1: Create the Check Function

Add your check function to the appropriate module in `backend/evals/structural/`:

- `module_checks.py` -- for learning module output checks
- `script_checks.py` -- for video script output checks
- `ppt_checks.py` -- for PowerPoint data checks

Each check function takes the output string as input and returns a `CheckResult`:

```python
from backend.evals.structural.types import CheckResult


def has_references_section(output: str) -> CheckResult:
    """Check that the module includes a References section."""
    if "## References" in output or "## Sources" in output:
        return CheckResult(passed=True, message="References section found")
    return CheckResult(
        passed=False,
        message="Missing References section (expected '## References' or '## Sources')"
    )
```

### Step 2: Register the Check

Add your check to the list of checks in the appropriate module:

```python
# In module_checks.py

MODULE_CHECKS = [
    has_all_sections,
    sections_in_order,
    min_length,
    has_blooms_verbs,
    has_curriculum_gap_tags,
    has_quick_check_answers,
    has_takeaway_prefixes,
    core_content_has_subheadings,
    has_references_section,  # your new check
]
```

### Step 3: Add a Test Case

Create a test in the corresponding test file:

```python
def test_has_references_section_present():
    output = "## Core Content\nSome content.\n\n## References\n- Source 1\n- Source 2"
    result = has_references_section(output)
    assert result.passed is True


def test_has_references_section_missing():
    output = "## Core Content\nSome content.\n\n## Key Takeaways\n- Point 1"
    result = has_references_section(output)
    assert result.passed is False
```

## Adding a New Judge

LLM judges use DeepSeek-V3 to evaluate outputs against weighted rubrics.

### Step 1: Subclass BaseJudge

Create a new judge in `backend/evals/judges/`:

```python
# backend/evals/judges/summary_judge.py

from backend.evals.judges.base import BaseJudge, Criterion


class SummaryJudge(BaseJudge):
    """Evaluates executive summary quality."""

    name = "summary"

    criteria = [
        Criterion(
            name="CONCISENESS",
            weight=0.25,
            description="Summary is concise and avoids unnecessary detail",
        ),
        Criterion(
            name="KEY_POINTS_COVERAGE",
            weight=0.30,
            description="All key points from the source material are represented",
        ),
        Criterion(
            name="ACCURACY",
            weight=0.25,
            description="Summary accurately reflects the source material",
        ),
        Criterion(
            name="READABILITY",
            weight=0.20,
            description="Summary is clear and easy to read",
        ),
    ]
```

!!! warning
    Criterion weights must sum to exactly **1.0**. The framework validates this at initialization and raises an error if the weights do not sum correctly.

### Step 2: Implement the `score()` Method

The `score()` method is inherited from `BaseJudge` and handles the LLM call. If you need custom pre-processing or post-processing, override it:

```python
class SummaryJudge(BaseJudge):
    # ... criteria defined above ...

    def build_prompt(self, output: str, context: dict) -> str:
        """Build the evaluation prompt sent to the LLM judge."""
        return f"""Evaluate the following executive summary on a 1-5 scale
for each criterion.

Source material topic: {context.get('topic_name', 'Unknown')}

Summary to evaluate:
{output}

Criteria:
{self._format_criteria()}

Respond with JSON: {{"criterion_name": score, ...}}"""
```

### Step 3: Register in EvalRunner

Add the judge to the `EvalRunner` configuration:

```python
# In backend/evals/runner.py

from backend.evals.judges.summary_judge import SummaryJudge

JUDGES = {
    "module": ModuleJudge(),
    "ppt": PPTJudge(),
    "script": ScriptJudge(),
    "consistency": ConsistencyJudge(),
    "summary": SummaryJudge(),  # your new judge
}
```

## Adding a New Dataset

Datasets provide input data and cached pipeline outputs for reproducible evaluation.

### Step 1: Create the Dataset Directory

```bash
mkdir -p backend/evals/datasets/<dataset_id>/
```

### Step 2: Create the Manifest

Create `manifest.json` with the dataset metadata:

```json
{
    "dataset_id": "my_dataset",
    "description": "Custom evaluation dataset for topic X",
    "version": "1.0",
    "topics": [
        {
            "topic_id": "topic_1",
            "topic_name": "Introduction to Topic 1",
            "input_pdfs": ["topic_1_syllabus.pdf", "topic_1_notes.pdf"],
            "curriculum_scope": "Covers fundamentals of Topic 1",
            "gap_summary": "Missing industry applications and recent developments"
        },
        {
            "topic_id": "topic_2",
            "topic_name": "Advanced Topic 2",
            "input_pdfs": ["topic_2_syllabus.pdf"],
            "curriculum_scope": "Covers theoretical foundations",
            "gap_summary": "Lacks hands-on implementation examples"
        }
    ]
}
```

### Step 3: Add Input PDFs

Place the input PDF files in the dataset directory:

```
backend/evals/datasets/my_dataset/
├── manifest.json
├── topic_1_syllabus.pdf
├── topic_1_notes.pdf
└── topic_2_syllabus.pdf
```

### Step 4: Generate Cached State

Run the pipeline to generate outputs and cache the state:

```bash
python -m backend.evals.capture_dataset --dataset my_dataset
```

This creates a `cached_state/` directory with the pipeline outputs:

```
backend/evals/datasets/my_dataset/
├── manifest.json
├── topic_1_syllabus.pdf
├── topic_1_notes.pdf
├── topic_2_syllabus.pdf
└── cached_state/
    ├── topic_1/
    │   └── pipeline_state.json
    └── topic_2/
        └── pipeline_state.json
```

### Step 5: Verify the Dataset

```bash
# List datasets to confirm yours appears
python -m backend.evals.cli list

# Run structural checks on the new dataset
python -m backend.evals.cli check --dataset my_dataset
```

## Best Practices

- **Keep checks deterministic**: Structural checks should produce the same result every time for the same input. Avoid randomness or external dependencies.
- **Test edge cases**: Include tests for empty strings, unicode content (GPT uses U+2019 curly apostrophes), and malformed inputs.
- **Weight criteria carefully**: Judge criteria weights should reflect the relative importance of each quality dimension for the specific output type.
- **Document your checks**: Include a clear docstring explaining what the check validates and why it matters.
- **Use small datasets for iteration**: Start with 2-3 topics when developing new checks or judges, then validate on the full dataset.
