"""Regenerate Agent 3 outputs using v2 prompt variants.

Uses cached Agent 1+2 state (topics, gap_summary) + ChromaDB to regenerate
modules and scripts with v2 prompts, then saves them for A/B comparison.

Usage:
    python -m backend.evals.regenerate_v2 --dataset cs224n --topics 5
"""

from __future__ import annotations

import argparse
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.config import settings
from backend.services.llm import get_llm
from backend.services.chromadb_store import ChromaStore
from backend.pipeline.agent_generate import (
    _generate_module,
    _generate_script_for_topic,
    _build_chroma_cache,
)
from backend.evals.prompt_registry.registry import PromptRegistry
from backend.evals.datasets.loader import load_cached_state


def regenerate(dataset_dir: str, max_topics: int = 5):
    """Regenerate modules and scripts using v2 prompts.

    Only regenerates topics that already have all 3 outputs in v1 cached state,
    so we can do a fair A/B comparison.
    """
    state = load_cached_state(dataset_dir)
    topics = state["topics"]
    gap_summary = state.get("gap_summary", [])
    curriculum_scope = state.get("curriculum_scope", "")
    cached_outputs = state.get("cached_outputs", {})

    # Filter to topics with all 3 v1 outputs
    full_topics = [
        t for t in topics
        if all(k in cached_outputs.get(t["name"], {}) for k in ["module_md", "ppt_json", "script"])
    ]
    print(f"[Regen] {len(full_topics)} topics have all 3 v1 outputs")

    # Limit to max_topics
    regen_topics = full_topics[:max_topics]
    print(f"[Regen] Regenerating {len(regen_topics)} topics with v2 prompts")
    for t in regen_topics:
        print(f"  - {t['name']}")

    # Load v2 prompts
    registry = PromptRegistry()
    generate_v2 = registry.get("generate", "v2")
    video_v2 = registry.get("video", "v2")

    if not generate_v2:
        print("[Regen] ERROR: generate_v2 prompt not found")
        return None
    if not video_v2:
        print("[Regen] ERROR: video_v2 prompt not found")
        return None

    print(f"[Regen] Loaded v2 prompts: generate ({len(generate_v2)} chars), video ({len(video_v2)} chars)")

    # Setup
    gap_lookup = {g.get("topic", ""): g for g in gap_summary}
    store = ChromaStore(settings.chroma_persist_dir)
    chroma_cache = _build_chroma_cache(store, regen_topics)

    llm_premium = get_llm("premium", temperature=settings.temp_structured)
    llm_mini = get_llm("mini")
    llm_script = get_llm("premium", temperature=settings.temp_creative)

    total = len(regen_topics)
    v2_outputs = {}

    # --- Step 1: Regenerate modules with generate_v2 ---
    print(f"\n[Regen] === Step 1: Generating {total} modules with generate_v2 ===")
    modules_v2 = [None] * total
    with ThreadPoolExecutor(max_workers=min(settings.max_workers, total)) as executor:
        future_to_idx = {
            executor.submit(
                _generate_module, i, regen_topics[i], total, chroma_cache,
                llm_premium, llm_mini, curriculum_scope, gap_lookup,
                prompt_template=generate_v2,
            ): i
            for i in range(total)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            modules_v2[idx] = future.result()

    # --- Step 2: Regenerate PPT slides (reuse v1 since no ppt_v2 prompt yet) ---
    # We keep the same PPT data from v1 for fair comparison
    print("\n[Regen] === Step 2: Reusing v1 PPT slides (no ppt_v2 variant) ===")

    # --- Step 3: Regenerate scripts with video_v2, using v2 modules as context ---
    print(f"\n[Regen] === Step 3: Generating {total} scripts with video_v2 ===")
    scripts_v2 = [None] * total
    used_hooks = []
    hooks_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=min(settings.max_workers, total)) as executor:
        future_to_idx = {}
        for i in range(total):
            topic_name = regen_topics[i]["name"]
            # Use v1 PPT slide data (same structure)
            topic_slide = cached_outputs.get(topic_name, {}).get("ppt_json", {})
            topic_gap = gap_lookup.get(topic_name, {})
            # Use v2 module as context for the script
            topic_module = modules_v2[i] or ""

            future = executor.submit(
                _generate_script_for_topic,
                i, topic_slide, topic_module, topic_gap,
                chroma_cache, llm_script, used_hooks, hooks_lock,
                prompt_template=video_v2,
            )
            future_to_idx[future] = i
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            scripts_v2[idx] = future.result()

    # --- Step 4: Assemble v2 cached outputs ---
    for i, topic in enumerate(regen_topics):
        name = topic["name"]
        v2_outputs[name] = {
            "module_md": modules_v2[i] or "",
            "ppt_json": cached_outputs.get(name, {}).get("ppt_json", {}),  # reuse v1
            "script": scripts_v2[i] or "",
        }

    # Save v2 state
    v2_state = {
        "topics": regen_topics,
        "gap_summary": [g for g in gap_summary if g.get("topic") in {t["name"] for t in regen_topics}],
        "curriculum_scope": curriculum_scope,
        "cached_outputs": v2_outputs,
    }

    cached_state_dir = os.path.join(dataset_dir, "cached_state")
    v2_path = os.path.join(cached_state_dir, "pipeline_state_v2.json")
    with open(v2_path, "w") as f:
        json.dump(v2_state, f, indent=2, default=str, ensure_ascii=False)
    print(f"\n[Regen] v2 outputs saved to {v2_path}")

    # Summary
    print(f"\n{'='*60}")
    print("Regeneration complete")
    print(f"  Topics regenerated: {total}")
    for name, data in v2_outputs.items():
        m_len = len(data.get("module_md", ""))
        s_words = len(data.get("script", "").split())
        s_chars = len(data.get("script", ""))
        print(f"  {name}: module={m_len} chars, script={s_words} words / {s_chars} chars")
    print(f"{'='*60}")

    return v2_state


def main():
    parser = argparse.ArgumentParser(description="Regenerate outputs with v2 prompts")
    parser.add_argument("--dataset", required=True, help="Dataset ID (e.g. cs224n)")
    parser.add_argument("--topics", type=int, default=5, help="Max topics to regenerate")
    args = parser.parse_args()

    dataset_dir = os.path.join("backend/evals/datasets", args.dataset)
    regenerate(dataset_dir, max_topics=args.topics)


if __name__ == "__main__":
    main()
