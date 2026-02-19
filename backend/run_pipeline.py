"""CLI entry point for the CR8 learning pipeline.

Usage:
    python -m backend.run_pipeline path/to/file1.pdf path/to/file2.pdf
    python -m backend.run_pipeline NLP_Course/CS224N_Downloads/Slides/*.pdf
"""

import sys
import time
import uuid

from backend.pipeline.graph import build_pipeline


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m backend.run_pipeline <file1.pdf> [file2.pdf ...]")
        sys.exit(1)

    file_paths = sys.argv[1:]
    print(f"\n{'='*60}")
    print(f"CR8 Learning Pipeline")
    print(f"{'='*60}")
    print(f"Input files: {len(file_paths)}")
    for f in file_paths:
        print(f"  - {f}")
    print(f"{'='*60}\n")

    pipeline = build_pipeline()

    initial_state = {
        "job_id": uuid.uuid4().hex[:12],
        "file_paths": file_paths,
        "topics": [],
        "raw_text": "",
        "gap_summary": [],
        "pdf_path": "",
        "current_stage": "starting",
    }

    start = time.time()
    result = pipeline.invoke(initial_state)
    elapsed = time.time() - start

    print(f"\n{'='*60}")
    print(f"Pipeline complete in {elapsed:.1f}s")
    print(f"Topics extracted: {len(result.get('topics', []))}")
    print(f"PDF: {result.get('pdf_path', 'N/A')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
