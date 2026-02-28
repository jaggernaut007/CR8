"""Run the pipeline and capture outputs as an eval dataset.

Usage:
    python -m backend.evals.capture_dataset --dataset cs224n \
        NLP_Course/CS224N_Downloads/Slides/01_Word_Vectors_I.pdf \
        NLP_Course/CS224N_Downloads/Slides/08_Transformers.pdf \
        NLP_Course/CS224N_Downloads/Slides/09_Pretraining.pdf
"""

from __future__ import annotations

import argparse
import glob as globmod
import json
import os
import time
import uuid

from backend.config import settings
from backend.pipeline.graph import build_pipeline


def capture(dataset_id: str, file_paths: list[str], formats: list[str]):
    """Run pipeline and save intermediate state + outputs for eval."""
    settings.output_formats = ",".join(formats)

    pipeline = build_pipeline()
    initial_state = {
        "job_id": uuid.uuid4().hex[:12],
        "file_paths": file_paths,
        "topics": [],
        "raw_text": "",
        "curriculum_scope": "",
        "gap_summary": [],
        "pdf_path": "",
        "ppt_path": "",
        "video_dir": "",
        "current_stage": "starting",
    }

    print(f"[Capture] Running pipeline with {len(file_paths)} files...")
    print(f"[Capture] Formats: {formats}")
    start = time.time()
    result = pipeline.invoke(initial_state)
    elapsed = time.time() - start
    print(f"[Capture] Pipeline completed in {elapsed:.1f}s")

    # Build cached state
    topics = result.get("topics", [])
    gap_summary = result.get("gap_summary", [])
    curriculum_scope = result.get("curriculum_scope", "")

    # Read raw outputs from sidecar JSON (saved by generate_node)
    cached_outputs = {}
    raw_outputs_files = sorted(globmod.glob("outputs/*_raw_outputs.json"), reverse=True)
    raw_outputs = {}
    if raw_outputs_files:
        try:
            with open(raw_outputs_files[0]) as f:
                raw_outputs = json.load(f)
            print(f"[Capture] Loaded raw outputs from {raw_outputs_files[0]}")
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Capture] WARNING: Could not read raw outputs: {e}")

    # Read scripts from disk
    video_dir = result.get("video_dir", "")
    scripts_dir = os.path.join(video_dir, "scripts") if video_dir else ""
    script_files = {}
    if scripts_dir and os.path.isdir(scripts_dir):
        for fname in sorted(os.listdir(scripts_dir)):
            if fname.endswith(".txt"):
                with open(os.path.join(scripts_dir, fname)) as f:
                    script_files[fname] = f.read()

    # Build per-topic cached outputs
    for topic in topics:
        name = topic["name"]
        topic_data = {}

        # Module markdown from raw outputs sidecar
        if name in raw_outputs:
            topic_data["module_md"] = raw_outputs[name].get("module_md", "")
            if "ppt_json" in raw_outputs[name]:
                topic_data["ppt_json"] = raw_outputs[name]["ppt_json"]

        # Match scripts by topic name in filename
        slug = name.lower().replace(" ", "_").replace("-", "_")
        for fname, content in script_files.items():
            fname_lower = fname.lower().replace("-", "_")
            if slug in fname_lower or any(
                word in fname_lower for word in slug.split("_") if len(word) > 3
            ):
                topic_data["script"] = content
                break

        cached_outputs[name] = topic_data

    # Save dataset
    dataset_dir = os.path.join("backend/evals/datasets", dataset_id)
    cached_state_dir = os.path.join(dataset_dir, "cached_state")
    os.makedirs(cached_state_dir, exist_ok=True)

    state = {
        "topics": topics,
        "gap_summary": gap_summary,
        "curriculum_scope": curriculum_scope,
        "raw_text": result.get("raw_text", "")[:5000],  # truncate for storage
        "cached_outputs": cached_outputs,
        "pipeline_result": {
            "pdf_path": result.get("pdf_path", ""),
            "ppt_path": result.get("ppt_path", ""),
            "video_dir": video_dir,
            "elapsed_seconds": elapsed,
        },
    }

    state_path = os.path.join(cached_state_dir, "pipeline_state.json")
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2, default=str, ensure_ascii=False)
    print(f"[Capture] Saved pipeline state to {state_path}")

    # Save manifest
    manifest = {
        "dataset_id": dataset_id,
        "description": f"Captured from {len(file_paths)} curriculum files",
        "version": "1.0",
        "input_pdfs": file_paths,
        "cached_state_path": cached_state_dir,
        "topics_count": len(topics),
        "gaps_count": sum(len(g.get("gaps", [])) for g in gap_summary),
    }
    manifest_path = os.path.join(dataset_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[Capture] Saved manifest to {manifest_path}")

    # Summary
    outputs_with_modules = sum(1 for v in cached_outputs.values() if v.get("module_md"))
    outputs_with_ppt = sum(1 for v in cached_outputs.values() if v.get("ppt_json"))
    outputs_with_scripts = sum(1 for v in cached_outputs.values() if v.get("script"))

    print(f"\n{'='*60}")
    print(f"Dataset '{dataset_id}' captured successfully")
    print(f"  Topics: {len(topics)}")
    print(f"  Gaps: {sum(len(g.get('gaps', [])) for g in gap_summary)}")
    print(f"  Modules captured: {outputs_with_modules}/{len(topics)}")
    print(f"  PPT slides captured: {outputs_with_ppt}/{len(topics)}")
    print(f"  Scripts captured: {outputs_with_scripts}/{len(topics)}")
    print(f"  Location: {dataset_dir}")
    print(f"{'='*60}")

    return state


def main():
    parser = argparse.ArgumentParser(description="Capture pipeline outputs as eval dataset")
    parser.add_argument("files", nargs="+", help="Curriculum PDF files")
    parser.add_argument("--dataset", required=True, help="Dataset ID (e.g. cs224n)")
    parser.add_argument(
        "--format", dest="formats", default="pdf,ppt,script",
        help="Output formats (default: pdf,ppt,script)",
    )
    args = parser.parse_args()
    formats = [f.strip() for f in args.formats.split(",")]
    capture(args.dataset, args.files, formats)


if __name__ == "__main__":
    main()
