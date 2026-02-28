# LLM Wrapper

**File**: `backend/services/llm.py`

Thin wrapper around `langchain-openai`'s `ChatOpenAI` with 4-tier model support.

## Usage

```python
from backend.services.llm import get_llm

nano = get_llm("nano")                          # GPT-5-nano -- summarization, extraction
mini = get_llm("mini")                          # GPT-5-mini -- analysis, structured output
premium = get_llm("premium")                    # GPT-5.1 -- creative generation
script_llm = get_llm("premium", temperature=0.55)  # Override temperature for creative writing
full = get_llm("full")                          # Alias for premium (backward compat)

response = mini.invoke("Summarize this text...")
print(response.content)
```

## Function Signature

```python
def get_llm(
    model: str = "mini",
    temperature: float | None = None,
) -> ChatOpenAI
```

Returns a configured LLM instance for the specified tier.

## Model Tiers

| Tier | Model | Default Temperature | Use Case |
|------|-------|-------------------|----------|
| `nano` | GPT-5-nano | 0.2 | Summarization, extraction |
| `mini` | GPT-5-mini | 0.3 | Analysis, structured output, gap analysis |
| `premium` | GPT-5.1 | 0.55 | Creative generation, critical modules, scripts |
| `full` | GPT-5.1 | 0.55 | Alias for premium (backward compatibility) |

Temperature defaults vary by tier. Override with the `temperature` parameter.
