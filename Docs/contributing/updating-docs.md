# Updating Documentation

This project uses [MkDocs](https://www.mkdocs.org/) with the [Material theme](https://squidfunk.github.io/mkdocs-material/) for documentation.

## Setup

```bash
pip install -e ".[docs]"
```

## Local Preview

```bash
make docs-serve
# Opens at http://localhost:8000 with live reload
```

## Adding a New Page

1. Create a new `.md` file in the appropriate `docs/` subdirectory
2. Add the page to the `nav` section in `mkdocs.yml`
3. Preview locally with `make docs-serve`

## Directory Structure

| Directory | Content |
|-----------|---------|
| `getting-started/` | Installation, quickstart, configuration |
| `architecture/` | System design, diagrams, technical decisions |
| `agents/` | Pipeline agent documentation |
| `services/` | Service layer documentation |
| `evals/` | Evaluation framework |
| `deployment/` | Docker, GCP deployment |
| `design/` | Research documents, design rationale |
| `api/` | Auto-generated API reference |
| `contributing/` | Development workflow |

## Writing Guidelines

### Admonitions

Use callout blocks for important information:

```markdown
!!! note
    This is a note.

!!! warning
    This is a warning.

!!! tip
    This is a tip.

!!! example
    This is an example.
```

### Code Blocks

Always specify the language:

````markdown
```python
def example():
    pass
```

```bash
make test
```
````

### Mermaid Diagrams

Create diagrams using fenced code blocks:

````markdown
``` mermaid
graph LR
    A --> B --> C
```
````

Material for MkDocs has native Mermaid.js support -- no plugins needed.

### Auto-Generated API Docs

Use mkdocstrings directives to auto-generate documentation from Python docstrings:

```markdown
::: backend.module.function_name
```

Add Google-style docstrings to your Python code:

```python
def my_function(param: str) -> dict:
    """Short description.

    Longer description if needed.

    Args:
        param: Description of the parameter.

    Returns:
        Description of the return value.
    """
```

### Internal Links

Use relative paths for cross-references:

```markdown
See the [Configuration guide](../getting-started/configuration.md) for details.
```

## Building

```bash
# Build with strict mode (catches broken links)
make docs-build

# Deploy to GitHub Pages (if configured)
make docs-deploy
```
