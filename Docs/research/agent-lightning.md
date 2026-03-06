# Research: Microsoft Agent Lightning

**Date researched:** 2026-03-06
**Library version:** agent-lightning>=0.3.0
**Researched by:** Claude Agent (research-assistant)
**Status:** Current

---

## Question Being Answered

> How can we use Microsoft Agent Lightning to optimize CR8's generation and research prompts using RL/APO techniques, and what's the integration path with our existing LangGraph pipeline?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| Official Documentation | https://microsoft.github.io/agent-lightning/latest/ | 2026-03-06 |
| GitHub Repository | https://github.com/microsoft/agent-lightning | 2026-03-06 |
| Microsoft Research Project | https://www.microsoft.com/en-us/research/project/agent-lightning/ | 2026-03-06 |
| SQL Agent Tutorial | https://microsoft.github.io/agent-lightning/latest/how-to/train-sql-agent/ | 2026-03-06 |
| Research Paper | https://arxiv.org/abs/2508.03680 | 2026-03-06 |

> **Note:** Agent Lightning is an RL framework designed for agentic workflows. Two modes apply to CR8: (1) APO requires only OpenAI API access, no GPU — can optimize prompts immediately; (2) full RL requires self-hosted model + 40GB GPU. Version 0.3.0 is current as of March 2026.

## What We Found

### Two Modes Relevant to CR8

**APO (Automatic Prompt Optimization)** — Zero GPU, API-only:
- Wraps CR8's `build_pipeline()` in a `LitAgent`
- Uses existing eval judges (`backend/evals/judges/`) as reward signal
- Optimizes prompt text via gradient-free search (~30 min per iteration)
- Works with any OpenAI-compatible model (default: gpt-4o-mini)

**Full RL Training** — Requires 40GB GPU:
- Fine-tunes self-hosted model weights (e.g., Qwen 1.5B)
- Uses GRPO (Group Relative Policy Optimization) algorithm
- ~10-20 hours per 100 training trajectories on NVIDIA L4
- Can optimize branching/routing decisions (not just prompts)

### Key API Concepts

| Class / Concept | Purpose | Notes |
|---|---|---|
| `LitAgent(agent_fn, config)` | Wraps any agent (LangGraph, AutoGen, etc.) | `agent_fn` must accept state dict, return updated state |
| `APOTrainer` | Optimizes prompts via API model, no GPU | Works with any OpenAI-compatible model |
| `RLTrainer` | Fine-tunes self-hosted model via GRPO/PPO | Requires 40GB+ GPU (NVIDIA L4+) |
| `RewardFunction` | Abstract base for custom reward scoring | Must return float in [0, 1] range |
| `GRPO()` / `PPO()` | RL algorithms for policy optimization | GRPO = faster convergence (default) |

### APO Integration Pattern

```python
from agent_lightning import LitAgent, APOTrainer, LitAgentConfig
from agent_lightning.reward import RewardFunction

# Wrap CR8's pipeline
lit_agent = LitAgent(
    agent_fn=lambda state: build_pipeline().invoke(state),
    config=LitAgentConfig(model="gpt-4o-mini", temperature=0.7),
)

# Reward function using CR8's eval judges
class CR8RewardFunction(RewardFunction):
    def __call__(self, trajectory: dict) -> float:
        scores = run_evals(trajectory.get("pdf_path"), trajectory.get("ppt_path"))
        total_weight = sum(s.weight for s in scores)
        weighted_sum = sum((s.score / 5.0) * s.weight for s in scores)
        return weighted_sum / total_weight if total_weight > 0 else 0.5

# Run optimization
trainer = APOTrainer(
    lit_agent=lit_agent,
    reward_fn=CR8RewardFunction(),
    num_iterations=5,
    batch_size=2,
)
optimized_prompts = trainer.train(training_trajectories)
```

## Known Gotchas

- **APO is stateless**: Each iteration re-evaluates from scratch. Requires pre-built trajectory pool.
- **Reward function stability**: Noisy eval judges cause divergence. Pre-validate on 20+ known good outputs.
- **No conditional branching in v0.3.0**: APO only optimizes prompts, not routing decisions.
- **Trajectory size**: Full pipeline state ~500 MB per run. Lazy-load from DB/GCS, don't cache all in memory.
- **Temperature sensitivity**: Optimization brittle with temp < 0.3. Use >= 0.5 during APO.
- **Full RL GPU OOM**: Qwen 1.5B on batch_size=4 needs ~40GB VRAM. Use bfloat16 (int8 not supported).

## What We Ruled Out

| Approach | Why Rejected |
|----------|-------------|
| HyperOpt / Optuna grid search | Too slow; APO converges faster via gradient-free optimization |
| Azure OpenAI fine-tuning | Vendor lock-in; AL is framework-agnostic |
| Manual prompt engineering | Subjective; AL provides data-driven optimization against eval scores |
| DSPy in-context learning | Doesn't handle sequential agentic workflows; AL specializes in this |

## Decision Made

> **v0.5 (now):** Research note only. No implementation.
>
> **v0.6:** Implement APO path. Zero GPU cost, ~30 min per optimization cycle. Requires:
> 1. `backend/agents/lit_agent_wrapper.py` — LitAgent wrapper
> 2. `backend/agents/cr8_reward.py` — RewardFunction using eval judges
> 3. CLI: `python scripts/train_agent.py apo --iterations 5`
> 4. Prompt versioning: `backend/prompts/versions/[timestamp]/`
>
> **v0.7+:** Full RL training if APO plateaus. Requires GPU infrastructure.

## Files This Will Affect (v0.6)

- `backend/agents/__init__.py` (new)
- `backend/agents/lit_agent_wrapper.py` (new)
- `backend/agents/cr8_reward.py` (new)
- `backend/prompts/versions/` (new directory)
- `backend/config.py` — APO settings
- `scripts/train_agent.py` (new)
- `pyproject.toml` — add `agent-lightning>=0.3`

---

*Re-verify if Agent Lightning has a major version bump past 1.0. Last verified: v0.3.0, March 2026.*
