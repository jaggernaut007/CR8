"""Versioned prompt registry for A/B testing prompt variants."""

from __future__ import annotations

import importlib
import os

# Maps (agent, variant) -> prompt template string
_REGISTRY: dict[tuple[str, str], str] = {}

# Default variants (v1) are loaded from the production prompts
_AGENT_TO_MODULE = {
    "generate": "backend.prompts.generate",
    "ppt": "backend.prompts.ppt",
    "video": "backend.prompts.video",
}

_AGENT_TO_ATTR = {
    "generate": "GENERATE_MODULE",
    "ppt": "STRUCTURE_SINGLE_TOPIC_SLIDE",
    "video": "SCRIPT_FROM_SLIDES",
}


class PromptRegistry:
    """Manage versioned prompt variants for evaluation."""

    def __init__(self):
        self._ensure_v1_loaded()

    def _ensure_v1_loaded(self):
        """Load production prompts as v1 if not already registered."""
        for agent, module_path in _AGENT_TO_MODULE.items():
            key = (agent, "v1")
            if key not in _REGISTRY:
                try:
                    mod = importlib.import_module(module_path)
                    attr = _AGENT_TO_ATTR[agent]
                    _REGISTRY[key] = getattr(mod, attr)
                except (ImportError, AttributeError):
                    pass

    def get(self, agent: str, variant: str = "v1") -> str | None:
        """Get a prompt variant. Returns None if not found."""
        # Check custom variant files first
        key = (agent, variant)
        if key in _REGISTRY:
            return _REGISTRY[key]

        # Try loading from variants directory
        variants_dir = os.path.join(os.path.dirname(__file__), "variants")
        variant_file = os.path.join(variants_dir, f"{agent}_{variant}.py")
        if os.path.isfile(variant_file):
            spec = importlib.util.spec_from_file_location(f"{agent}_{variant}", variant_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            prompt = getattr(mod, "PROMPT", None)
            if prompt:
                _REGISTRY[key] = prompt
                return prompt

        return None

    def register(self, agent: str, variant: str, prompt: str):
        """Register a prompt variant in memory."""
        _REGISTRY[(agent, variant)] = prompt

    def list_variants(self, agent: str) -> list[str]:
        """List all registered variants for an agent."""
        variants = set()
        for (a, v) in _REGISTRY:
            if a == agent:
                variants.add(v)
        # Also check variant files on disk
        variants_dir = os.path.join(os.path.dirname(__file__), "variants")
        if os.path.isdir(variants_dir):
            prefix = f"{agent}_"
            for f in os.listdir(variants_dir):
                if f.startswith(prefix) and f.endswith(".py"):
                    v = f[len(prefix):-3]
                    variants.add(v)
        return sorted(variants)

    def list_agents(self) -> list[str]:
        """List all agents with registered prompts."""
        agents = set(a for a, _ in _REGISTRY)
        return sorted(agents)
