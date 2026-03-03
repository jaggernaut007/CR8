# backend/pipeline/

LangGraph 3-agent state machine for the CR8 learning pipeline.

## Files

| File | Role |
|------|------|
| `graph.py` | Graph definition and compilation — **entry point** |
| `state.py` | All pipeline state as a typed `TypedDict` |
| `agent_ingest.py` | Agent 1: extract topics, complexity scores, structure from PDFs |
| `agent_research.py` | Agent 2: enrich topics with Tavily search + ChromaDB context |
| `agent_generate.py` | Agent 3: generate learning guide content per topic |

## Data Flow

```
graph.py compiles the graph:
    START
      → agent_ingest     (topics: List[Topic], complexity_scores: Dict)
      → agent_research   (research_context: Dict[topic, List[SearchResult]])
      → agent_generate   (outputs: Dict[format, content])
    END
```

## State Schema

All state lives in `state.py` as a `TypedDict`. Adding new pipeline data = add a field here.
Never store state in agent function local variables between nodes.

## Model Routing

Agents call `backend/services/llm.py` with a model tier argument:
- `ModelTier.NANO` — fast extraction in ingest
- `ModelTier.MINI` — moderate tasks in research
- `ModelTier.DEFAULT` — main generation in generate
- `ModelTier.PREMIUM` — critical quality checks

## Rules
- Each agent function receives the full state and returns the full updated state
- Conditional edges (e.g., route based on complexity) use named constants from `state.py`
- New pipeline steps = new agent file + new node in `graph.py` + new state fields in `state.py`
