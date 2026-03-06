---
description: Code quality standards for all Python files. Enforces short functions, thorough commenting, structured logging, and clean patterns.
paths:
  - "**/*.py"
---

# CR8 Code Quality Standards

## 1. Short Functions (Hard Rules)
- Every function must do ONE thing. If you can't describe it in one sentence, split it.
- **Hard limit: 25 statements per function** (enforced by ruff PLR0915).
- **Max 5 arguments per function** (enforced by ruff PLR0913). Use a dataclass/TypedDict for more.
- **Max cyclomatic complexity: 10** (enforced by ruff C901). Flatten nested if/else with early returns or guard clauses.
- **Max 12 branches per function** (enforced by ruff PLR0912).
- **Max 6 return statements per function** (enforced by ruff PLR0911).
- Extract early: validation, transformation, and I/O should be separate functions.
- Prefer multiple small, well-named functions over one long function with comments separating sections.

## 2. Comments and Docstrings
- Every module must have a module-level docstring explaining its purpose.
- Every public function and class must have a Google-style docstring:
  ```python
  def build_slides(topics: list[Topic], template: str) -> Path:
      """Build a PPTX slide deck from structured topics.

      Args:
          topics: Ordered list of topics with content and diagrams.
          template: Path to the PPTX template file.

      Returns:
          Path to the generated .pptx file.
      """
  ```
- Add inline comments for non-obvious logic: regex patterns, business rules, workarounds, magic numbers.
- Do NOT add comments that just restate the code (e.g., `# increment counter` above `counter += 1`).
- Never leave commented-out code in the codebase (enforced by ruff ERA001). Delete it; git has history.

## 3. Logging (Mandatory)
- Every module must create a logger at the top:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  ```
- **What to log at each level:**
  - `logger.debug()` — variable values, intermediate state, loop iterations (dev troubleshooting)
  - `logger.info()` — function entry/exit with key params, successful operations, milestones
  - `logger.warning()` — recoverable issues, fallbacks triggered, deprecated code paths
  - `logger.error()` — caught exceptions, failed operations (always include `exc_info=True`)
  - `logger.critical()` — unrecoverable failures that stop the pipeline
- **Mandatory logging points:**
  - Function entry: log the function name and key input params at INFO level
  - Function exit: log success and any key output metrics (e.g., "Generated 12 slides in 3.2s")
  - Exception handlers: always log at ERROR with `exc_info=True`
  - External API calls: log before (INFO) and after (INFO success, ERROR failure)
  - Conditional branches indicating unusual state: log at WARNING
- **Use lazy formatting** (enforced by ruff G rules — no f-strings or .format() in log calls):
  ```python
  # CORRECT — lazy formatting, string only built if level is active
  logger.info("Building PDF: topics=%d, template=%s", len(topics), template_name)

  # WRONG — f-string always evaluated even if INFO is disabled
  logger.info(f"Building PDF: topics={len(topics)}, template={template_name}")
  ```
- Never use `print()` for logging (enforced by ruff T20). Use the logger.
- Never log sensitive data (API keys, user credentials, full file contents).

## 4. Code Cleanliness (Enforced by Ruff)
- **No mutable default arguments** (ruff B006): use `None` + conditional instead of `def f(x=[])`.
- **No builtin shadowing** (ruff A): never name variables `list`, `dict`, `type`, `id`, `input`, `map`, `filter`.
- **Use modern Python syntax** (ruff UP): `dict` not `typing.Dict`, `X | None` not `Optional[X]`, etc.
- **Clean return statements** (ruff RET): no superfluous `else` after `return`, no unnecessary `return None`.
- **Simplify where possible** (ruff SIM): merge duplicate `isinstance()`, use `contextlib.suppress()`, prefer ternaries for simple conditionals.
- **No bare `except:`** — always catch a specific exception type.
- **No unused variables** — if you must ignore a value, prefix with `_`.

## 5. Function Design Principles
- Use early returns to avoid deep nesting:
  ```python
  # GOOD — flat, easy to read
  def process(data):
      if not data:
          return []
      if not data.is_valid():
          logger.warning("Invalid data: id=%s", data.id)
          return []
      return _transform(data)

  # BAD — nested pyramid
  def process(data):
      if data:
          if data.is_valid():
              return _transform(data)
          else:
              return []
      else:
          return []
  ```
- Keep I/O at the edges — pure logic in the middle, side effects (file I/O, API calls, DB) at the boundaries.
- If a function has a try/except that wraps most of its body, extract the body into a helper.
