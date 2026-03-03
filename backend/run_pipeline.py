"""CLI entry point for the CR8 learning pipeline.

Usage:
    python -m backend.run_pipeline path/to/file1.pdf
    python -m backend.run_pipeline --format pdf,script slides/*.pdf
    python -m backend.run_pipeline --format pdf,script,video slides/*.pdf
"""

import argparse
import sys
import time
import uuid

from backend.config import settings
from backend.pipeline.graph import build_pipeline

VALID_FORMATS = {"pdf", "ppt", "script", "video"}


def main():
    parser = argparse.ArgumentParser(
        description="CR8 Learning Pipeline — curriculum in, learning guide out.",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Curriculum files to process (.pdf, .pptx)",
    )
    parser.add_argument(
        "--format",
        dest="output_formats",
        default="pdf",
        help="Comma-separated output formats: pdf,script,video (default: pdf)",
    )
    args = parser.parse_args()

    # Parse and validate formats
    formats = [f.strip() for f in args.output_formats.split(",")]
    invalid = set(formats) - VALID_FORMATS
    if invalid:
        print(f"Error: Invalid format(s): {', '.join(invalid)}")
        print(f"Valid formats: {', '.join(sorted(VALID_FORMATS))}")
        sys.exit(1)

    # Override settings with CLI flags
    settings.output_formats = ",".join(formats)

    # Validate video provider config when video rendering is requested
    if "video" in settings.output_formats_list:
        missing = []
        if settings.video_provider == "synthesia":
            if not settings.synthesia_api_key:
                missing.append("SYNTHESIA_API_KEY")
            if not settings.synthesia_avatar_id:
                missing.append("SYNTHESIA_AVATAR_ID")
        else:
            if not settings.heygen_api_key:
                missing.append("HEYGEN_API_KEY")
            if not settings.heygen_avatar_id:
                missing.append("HEYGEN_AVATAR_ID")
            if not settings.heygen_voice_id:
                missing.append("HEYGEN_VOICE_ID")
        if missing:
            provider = settings.video_provider
            print(f"Error: --format video ({provider}) requires these env vars: {', '.join(missing)}")
            print("Set them in your .env file. See .env.example for reference.")
            print("Tip: Use --format pdf,script to generate scripts without video rendering.")
            sys.exit(1)

    file_paths = args.files
    print(f"\n{'='*60}")
    print("CR8 Learning Pipeline")
    print(f"{'='*60}")
    print(f"Input files: {len(file_paths)}")
    for f in file_paths:
        print(f"  - {f}")
    print(f"Output formats: {', '.join(settings.output_formats_list)}")
    if "script" in settings.output_formats_list or "video" in settings.output_formats_list:
        print(f"Video topic limit: {settings.video_topic_limit}")
    print(f"{'='*60}\n")

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
        "output_formats": ",".join(formats),
        "current_stage": "starting",
    }

    start = time.time()
    result = pipeline.invoke(initial_state)
    elapsed = time.time() - start

    print(f"\n{'='*60}")
    print(f"Pipeline complete in {elapsed:.1f}s")
    print(f"Topics extracted: {len(result.get('topics', []))}")
    if result.get("pdf_path"):
        print(f"PDF: {result['pdf_path']}")
    if result.get("ppt_path"):
        print(f"PPT: {result['ppt_path']}")
    if result.get("video_dir"):
        print(f"Video scripts: {result['video_dir']}/scripts/")
    print(f"{'='*60}\n")


def run_job(file_paths: list[str], formats: list[str]) -> dict:
    """Run pipeline programmatically. Called by web frontend.

    Returns the LangGraph result state dict.
    Raises ValueError for invalid inputs.
    """
    invalid = set(formats) - VALID_FORMATS
    if invalid:
        raise ValueError(f"Invalid format(s): {', '.join(invalid)}")

    if "video" in formats:
        raise ValueError(
            "Video generation is not yet available. "
            "Use formats: pdf, ppt, script."
        )

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
        "output_formats": ",".join(formats),
        "current_stage": "starting",
    }
    return pipeline.invoke(initial_state)


if __name__ == "__main__":
    main()
