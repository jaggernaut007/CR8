"""Regenerate PDF and PPT from a raw_outputs.json file.

Usage:
    python3 regenerate_from_raw.py outputs/20260227_194337_raw_outputs.json
"""

import json
import sys
import os
from datetime import datetime

from backend.services.pdf_builder import build_pdf
from backend.services.ppt_builder import build_gap_ppt


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 regenerate_from_raw.py <raw_outputs.json>")
        sys.exit(1)

    raw_path = sys.argv[1]
    with open(raw_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Separate _slide_data from topic entries
    slide_data = raw.pop("_slide_data", None)

    # Build topics list and modules_md list (preserving order)
    topics = []
    modules_md = []
    for topic_name, data in raw.items():
        topics.append({"name": topic_name})
        modules_md.append(data["module_md"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("outputs", exist_ok=True)

    # --- Regenerate PDF ---
    pdf_path = os.path.join("outputs", f"{timestamp}_learning_guide.pdf")
    print(f"[Regenerate] Building PDF with {len(topics)} topics...")
    build_pdf(
        title="Market-Enriched Learning Guide",
        topics=topics,
        modules_md=modules_md,
        output_path=pdf_path,
    )
    print(f"[Regenerate] PDF written to {pdf_path}")

    # --- Regenerate PPT ---
    if slide_data:
        ppt_path = os.path.join("outputs", f"{timestamp}_gap_analysis.pptx")
        print("[Regenerate] Building PPT...")
        build_gap_ppt(slide_data=slide_data, output_path=ppt_path)  # returns (path, map)
        print(f"[Regenerate] PPT written to {ppt_path}")
    else:
        print("[Regenerate] No _slide_data found in raw outputs, skipping PPT.")

    print("[Regenerate] Done!")


if __name__ == "__main__":
    main()
