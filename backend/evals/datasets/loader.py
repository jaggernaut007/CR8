"""Load and validate eval datasets from disk."""

from __future__ import annotations

import json
import os

from backend.evals.datasets.schema import DatasetManifest, EvalInput


def load_manifest(dataset_dir: str) -> DatasetManifest:
    """Load a dataset manifest from a directory."""
    manifest_path = os.path.join(dataset_dir, "manifest.json")
    with open(manifest_path) as f:
        return DatasetManifest(**json.load(f))


def load_cached_state(dataset_dir: str) -> dict:
    """Load cached Agent 1+2 state (topics, gap_summary, curriculum_scope, raw_text)."""
    state_path = os.path.join(dataset_dir, "cached_state", "pipeline_state.json")
    with open(state_path) as f:
        return json.load(f)


def build_eval_inputs(state: dict) -> list[EvalInput]:
    """Build eval input cases from cached pipeline state."""
    topics = state.get("topics", [])
    gap_summary = state.get("gap_summary", [])
    curriculum_scope = state.get("curriculum_scope", "")
    gap_lookup = {g.get("topic", ""): g for g in gap_summary}

    inputs = []
    for topic in topics:
        name = topic["name"]
        inputs.append(EvalInput(
            case_id=f"{name.lower().replace(' ', '_')}",
            topic_name=name,
            curriculum_scope=curriculum_scope,
            gap_summary=gap_lookup.get(name, {}),
        ))
    return inputs


def list_datasets(base_dir: str) -> list[str]:
    """List available dataset IDs."""
    datasets = []
    for name in os.listdir(base_dir):
        manifest = os.path.join(base_dir, name, "manifest.json")
        if os.path.isfile(manifest):
            datasets.append(name)
    return sorted(datasets)
