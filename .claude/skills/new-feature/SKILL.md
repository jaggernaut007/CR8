---
name: new-feature
description: Scaffolds a new feature across all required CR8 locations — service, tests, prompts, docs, ADR. Classifies the feature type, routes to prerequisite agents (adr-writer, research-assistant), then produces an ordered creation checklist. Triggers on "new feature", "scaffold a feature", "start a new service", "add a new pipeline output", "set up a new feature".
---

# New Feature Skill

Ensures every new feature is created consistently across all required
locations in the CR8 codebase. Does not create files itself — produces
an ordered checklist and routes to the correct agents at each step.

## Step 1 — Classify the feature

Ask the developer three questions:

1. **What** is the feature? (one sentence)
2. **What type** is it?
   - **Type A — New service**: wraps an external API or adds an output format
     (e.g., widget_builder.py)
   - **Type B — New pipeline agent**: adds a LangGraph node
     (e.g., a validation stage between Research and Generate)
   - **Type C — New endpoint only**: adds a route to frontend/app.py
3. **Does this add a new pip dependency** (external library or API)?

Do not proceed until all three are answered.

## Step 2 — Check for existing ADR or research note

```bash
ls docs/adr/
ls docs/research/
```

Check if an ADR or research note already covers this area.
If yes, read it and report any constraints it imposes on the design.

## Step 3 — Route to adr-writer (if required)

Invoke the adr-writer agent if ANY of:
- Type A and involves a new external API (not just a new output builder)
- Type B (any new pipeline agent requires an ADR)
- New pip dependency (question 3 = yes)

> Invoking adr-writer: "Create an ADR for [feature name]."

Wait for ADR to be committed BEFORE continuing. ADR first, code second.

If none of the above apply, skip this step.

## Step 4 — Route to research-assistant (if new dependency)

If question 3 was YES, invoke the research-assistant agent:
> Invoking research-assistant: "Research [library/API] before implementing [feature]."

Wait for research note in docs/research/ before continuing.

## Step 5 — Produce the file creation checklist

Based on feature type, produce an ordered checklist with exact paths.

### Type A — New service (example: `widget_builder`)

```
New Feature Scaffold: widget_builder
─────────────────────────────────────
[ ] 1. backend/services/widget_builder.py
       Pattern: follow pdf_builder.py
       One public function, all external calls here

[ ] 2. backend/prompts/widget.py
       Pattern: follow generate.py
       Prompt constants only, no inline strings in services

[ ] 3. backend/tests/test_widget_builder.py
       → Route to test-writer:
         "Write tests for backend/services/widget_builder.py"

[ ] 4. mk-docs/services/widget-builder.md + update mkdocs.yml nav
       → Route to docs-writer:
         "Write docs for my new widget_builder service"

[ ] 5. backend/pipeline/agent_generate.py (if format hooks into generate)
       Add format routing: check output_formats, call build_widget()
       Update backend/pipeline/state.py if new state field needed

[ ] 6. CHANGELOG.md — Unreleased section (docs-writer handles this)
```

### Type B — New pipeline agent (example: `agent_validate`)

```
New Feature Scaffold: agent_validate
─────────────────────────────────────
[ ] 1. backend/pipeline/state.py
       Add new TypedDict fields — state is the contract, always first

[ ] 2. backend/pipeline/agent_validate.py
       Pattern: follow agent_research.py
       One public function: validate_node(state) -> PipelineState

[ ] 3. backend/pipeline/graph.py
       Add node + edges, follow conditional edge pattern

[ ] 4. backend/run_pipeline.py
       Initialise new state fields in starting state dict

[ ] 5. backend/tests/test_pipeline_agents.py
       → Route to test-writer:
         "Write tests for backend/pipeline/agent_validate.py"

[ ] 6. mk-docs/agents/validate.md + update mkdocs.yml nav
       → Route to docs-writer:
         "Document the new validate agent"
```

### Type C — New endpoint only

```
New Feature Scaffold: /api/new-endpoint
────────────────────────────────────────
[ ] 1. frontend/app.py
       Pydantic request/response models, get_current_user dependency,
       HTTPException with correct status codes

[ ] 2. frontend/tests/test_api.py
       → Route to test-writer:
         "Write tests for the new endpoint in frontend/app.py"

[ ] 3. mk-docs/api/frontend.md
       → Route to docs-writer:
         "Update API docs for my new endpoint"
```

## Step 6 — Track and close

As each item is completed, the developer marks it done. When all are complete:

```bash
make lint && make test
```

If both pass:
> All scaffold items complete. Run `/commit-ready` to validate before committing.

## Rules

- Never create files yourself — produce the checklist and route to agents
- ADR must be committed BEFORE feature code (Step 3)
- Research note must exist BEFORE service code (Step 4)
- State schema changes (state.py) always come before agent code in Type B
- Do not skip test-writer routing — "tests later" becomes "tests never"
- If the developer says "just the service file for now", remind them:
  CONTRIBUTING.md requires tests for every new feature before the task is complete
