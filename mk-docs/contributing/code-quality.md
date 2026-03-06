# Code Quality Guide

This page documents the code quality standards enforced across the CR8 codebase by Ruff lint rules and Claude Code agent rules.

---

## Short Functions

Every function should do **one thing**. If you can't describe it in one sentence, split it.

### Enforced Limits

| Constraint | Limit | Ruff Rule | What Triggers It |
|------------|-------|-----------|------------------|
| Statements per function | 25 | PLR0915 | Functions with too many lines of executable code |
| Arguments per function | 5 | PLR0913 | Functions accepting too many parameters |
| Cyclomatic complexity | 10 | C901 | Deeply nested if/else/loop chains |
| Branches per function | 12 | PLR0912 | Too many if/elif/else/for/while branches |
| Return statements | 6 | PLR0911 | Functions with too many exit points |

### How to Fix Violations

**Too many statements** — Extract helper functions:

```python
# BAD: 30+ statement monolith
def process_document(doc):
    # validate...
    # parse...
    # transform...
    # save...

# GOOD: Decomposed into focused helpers
def process_document(doc):
    validated = _validate_document(doc)
    parsed = _parse_sections(validated)
    transformed = _transform_content(parsed)
    return _save_output(transformed)
```

**Too many arguments** — Use a config object:

```python
# BAD: 8 positional args
def build_video(slides, audio, template, fps, width, height, codec, preset):
    ...

# GOOD: Group related params
@dataclass
class VideoConfig:
    fps: int = 30
    width: int = 1920
    height: int = 1080
    codec: str = "h264"
    preset: str = "fast"

def build_video(slides: list, audio: Path, template: str, config: VideoConfig):
    ...
```

**High complexity** — Use early returns (guard clauses):

```python
# BAD: Deeply nested
def handle_result(result):
    if result:
        if result.status == "ok":
            if result.data:
                return process(result.data)
            else:
                return default()
        else:
            raise Error(result.status)
    else:
        raise Error("no result")

# GOOD: Flat with early returns
def handle_result(result):
    if not result:
        raise Error("no result")
    if result.status != "ok":
        raise Error(result.status)
    if not result.data:
        return default()
    return process(result.data)
```

---

## Logging Standards

Every module must have structured logging. No exceptions.

### Setup

```python
import logging

logger = logging.getLogger(__name__)
```

### Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| `DEBUG` | Variable values, intermediate state, loop iterations | `logger.debug("Chunk %d: %d chars", i, len(chunk))` |
| `INFO` | Function entry/exit, successful operations, milestones | `logger.info("Generated %d slides in %.1fs", count, elapsed)` |
| `WARNING` | Recoverable issues, fallbacks, deprecated paths | `logger.warning("ChromaDB empty, falling back to web search")` |
| `ERROR` | Caught exceptions, failed operations | `logger.error("OpenAI call failed", exc_info=True)` |
| `CRITICAL` | Unrecoverable failures that stop the pipeline | `logger.critical("No API key configured, aborting")` |

### Mandatory Logging Points

1. **Function entry** — Log key input parameters at INFO:
   ```python
   def build_pdf(topics, template_name):
       logger.info("Building PDF: topics=%d, template=%s", len(topics), template_name)
   ```

2. **Function exit** — Log success and output metrics at INFO:
   ```python
       logger.info("PDF complete: %d pages, %.1f MB", page_count, size_mb)
       return output_path
   ```

3. **Exception handlers** — Always log at ERROR with `exc_info=True`:
   ```python
   except OpenAIError as e:
       logger.error("LLM call failed for topic=%s", topic_name, exc_info=True)
       raise
   ```

4. **External API calls** — Log before and after:
   ```python
   logger.info("Calling OpenAI: model=%s, tokens=%d", model, max_tokens)
   response = client.chat.completions.create(...)
   logger.info("OpenAI response: tokens_used=%d", response.usage.total_tokens)
   ```

5. **Unusual branches** — Log at WARNING:
   ```python
   if not slides:
       logger.warning("No slides generated for topic=%s, using fallback", topic)
   ```

### Lazy Formatting (Enforced by Ruff G Rules)

```python
# CORRECT — string only built if level is active
logger.info("Processing %d items for user=%s", count, user_id)

# WRONG — f-string always evaluated, even if INFO is disabled
logger.info(f"Processing {count} items for user={user_id}")

# WRONG — .format() always evaluated
logger.info("Processing {} items".format(count))
```

### What NOT to Log

- API keys, tokens, or credentials
- Full file contents or large data structures
- User passwords or personal data
- Anything that would make logs unsafe to share

---

## Comments and Docstrings

### Module Docstrings

Every `.py` file starts with a docstring explaining its purpose:

```python
"""PDF builder service.

Converts structured topic content into formatted PDF learning guides
using fpdf2. Handles Unicode, code blocks, and markdown formatting.
"""
```

### Function Docstrings (Google Style)

Every public function and class has a docstring:

```python
def build_slides(topics: list[Topic], template: str) -> Path:
    """Build a PPTX slide deck from structured topics.

    Args:
        topics: Ordered list of topics with content and diagrams.
        template: Path to the PPTX template file.

    Returns:
        Path to the generated .pptx file.

    Raises:
        FileNotFoundError: If the template file doesn't exist.
    """
```

### Inline Comments

- Add comments for **non-obvious logic**: regex patterns, business rules, workarounds, magic numbers
- Do NOT add comments that restate the code
- Never leave commented-out code — delete it (enforced by ERA001)

```python
# GOOD — explains WHY
# ChromaDB returns cosine distance (0-2), convert to similarity (0-1)
similarity = 1 - (distance / 2)

# BAD — restates WHAT
# Calculate similarity
similarity = 1 - (distance / 2)
```

---

## Code Cleanliness Rules

### Full Ruff Rule Reference

| Code | Category | What It Catches | Auto-fixable |
|------|----------|----------------|--------------|
| E/W/F | Defaults | Syntax errors, whitespace, unused imports | Most |
| UP | pyupgrade | Outdated syntax (`typing.Dict` -> `dict`) | Yes |
| B | bugbear | Mutable defaults, bad exception handling | Some |
| A | builtins | Shadowing `list`, `dict`, `type`, `id` | No |
| T20 | print | `print()` in production code | No |
| RET | return | Superfluous `else` after `return` | Some |
| SIM | simplify | Duplicate `isinstance()`, nested `with` | Some |
| PIE | pie | Unnecessary placeholders, dict unpacking | Some |
| C90 | McCabe | Cyclomatic complexity > 10 | No |
| G | logging-format | f-strings/`.format()` in log calls | Yes |
| ERA | eradicate | Commented-out dead code | Yes |
| PLR | pylint | Function size limits (args, statements, etc.) | No |
| RUF | ruff | Ruff-specific cleanup rules | Some |

### Per-File Exceptions

Test files and eval scripts have relaxed rules (configured in `pyproject.toml`):

| File Pattern | Ignored Rules | Reason |
|-------------|---------------|--------|
| `**/tests/**/*.py` | T201, PLR2004, PLR0913, PLR0915 | Tests are verbose by nature |
| `backend/evals/**/*.py` | T201, PLR2004 | CLI output and threshold comparisons |
| `scripts/**/*.py` | T201 | Script output |

### Running Lint Checks

```bash
# Full check
make lint

# Auto-fix safe violations
ruff check . --fix

# See violation statistics
ruff check . --statistics

# Check a single category
ruff check . --select C901

# Preview unsafe fixes before applying
ruff check . --unsafe-fixes --diff
```

---

## Quick Reference

Before writing any function, check:

- [ ] Does it do ONE thing? Can I describe it in one sentence?
- [ ] Is it under 25 statements?
- [ ] Does it have 5 or fewer arguments?
- [ ] Does it start with `logger.info(...)` logging key inputs?
- [ ] Does it end with `logger.info(...)` logging the result?
- [ ] Do all `except` blocks log with `exc_info=True`?
- [ ] Does it have a Google-style docstring?
- [ ] Are all log calls using lazy `%s` formatting (no f-strings)?
- [ ] Does `ruff check .` pass clean?
