# Testing Guide

CR8 has a comprehensive automated test suite of **507 tests** covering the full stack: pipeline agents, eval harness, structural checks, services, LangGraph graph integration, all FastAPI endpoints, GCS/GPU service clients, and the GPU microservice worker. All tests run with **zero real API calls** — all LLMs, web search, ChromaDB, GCS, and the GPU service are mocked where needed.

---

## Running Tests

```bash
# Full suite (recommended)
python3 -m pytest backend/tests/ frontend/tests/ --tb=short -q

# Backend only
python3 -m pytest backend/tests/ -v

# Specific module
python3 -m pytest backend/tests/test_structural_checks.py -v

# Property-based tests with more examples
python3 -m pytest backend/tests/test_structural_checks.py -k "PropertyBased" \
  --hypothesis-seed=0

# Snapshot update (run once after schema changes)
python3 -m pytest backend/tests/test_eval_harness.py::TestEvalResultSnapshot \
  --snapshot-update
```

---

## Test Inventory

### Backend Tests

| File | Tests | What it covers |
|------|-------|----------------|
| `test_structural_checks.py` | 63 | All L1 structural check modules + `_sanitize` property-based tests |
| `test_eval_harness.py` | 28 | Comparator winner/regression math, scorer L1-only, syrupy snapshots, hypothesis property tests |
| `test_graph_integration.py` | 8 | LangGraph `build_pipeline()` compilation, node wiring, state propagation |
| `test_pipeline_agents.py` | 45 | `ingest_node`, `research_node`, `generate_node`, `_validate_module`, `_detect_hook_type`, `_sanitize` |
| `test_services.py` | 13 | `get_llm()` tier routing, `search()` with mocked Tavily, ChromaDB edge cases |
| `test_bug_fixes.py` | 21 | Regression suite for all March 2026 hardening fixes |
| `test_pdf_builder.py` | 20+ | PDF generation: Unicode, malformed markdown, code blocks, special chars |
| `test_chromadb_store.py` | 7 | Add/query, reset, isolation, custom IDs, metadata, empty collection, `n_results` limit |
| `test_file_parser.py` | 12 | PDF extraction, non-empty pages, multiple files, missing file, empty PDF, unsupported type; `export_slides_as_images()` PDF and PPTX paths, output dir creation, path validation |
| `test_script_parser.py` | 10 | `[SLIDE N]` marker parsing, empty scripts, malformed markers, multi-segment scripts |
| `test_tts_engine.py` | 10 | `synthesize()` and `synthesize_segments()` with `soundfile` stubbed via `sys.modules` |
| `test_run_pipeline.py` | 9 | `run_job()` validation (invalid format, missing video provider keys, unknown provider), pipeline invocation, state shape, unique job IDs |
| `test_video_builder.py` | 11 | URL guard, download helpers, Kokoro two-phase pipeline (TTS + parallel compose), shared engine, empty `slide_images` guard |
| `test_gcs_client.py` | 12 | `upload_job_inputs()`, `download_videos()`, `cleanup_job()` with mocked `google.cloud.storage` |
| `test_gpu_client.py` | 12 | `submit_job()`, `poll_until_complete()` (complete/error/timeout paths), identity token fetch, `is_available()` |
| `test_agent_generate_dispatch.py` | 8 | `_build_videos_dispatch()`: GPU path (GCS upload → submit → poll → download), local fallback path |

### Frontend Tests

| File | Tests | What it covers |
|------|-------|----------------|
| `frontend/tests/test_api.py` | 90 | All FastAPI endpoints: auth, upload (PDF + PPTX), start, progress (including `warnings` field), download; PPTX magic byte validation; video UI (Kokoro TTS checkbox enabled, warning box) |
| `frontend/tests/test_progress_capture.py` | 39 | Stage parsing, progress %age (updated STAGE_WEIGHTS), thread safety, stage time budgets |

### GPU Service Tests

| File | Tests | What it covers |
|------|-------|----------------|
| `gpu_service/tests/test_worker.py` | 15 | Worker job lifecycle: GCS download, Kokoro TTS, ffmpeg encode, GCS upload, error handling |
| `gpu_service/tests/test_app.py` | 10 | FastAPI endpoints: `/health`, `POST /api/v1/video-jobs`, `GET /api/v1/video-jobs/{id}` |

**Total: 507 tests — 0 real API calls**

---

## Test Architecture

### Three Testing Layers

```
Layer 1 — Pure Functions (no mocking needed)
  structural checks, _sanitize, _validate_module, _detect_hook_type,
  compute_weighted_total

Layer 2 — Unit Tests with Mocked Dependencies
  agent nodes, services, comparator, scorer L1-only
  all LLMs/ChromaDB/Tavily/GCS/GPU service replaced with unittest.mock.MagicMock

Layer 3 — Integration & Regression
  LangGraph graph routing, API endpoint flows, March 2026 bug fixes
```

### Shared Fixtures (`backend/tests/conftest.py`)

All test files share a common fixture set:

| Fixture | Returns | Use case |
|---------|---------|----------|
| `mock_llm` | `MagicMock` with `.invoke()` stubbed | Replace any LLM call |
| `base_pipeline_state` | Valid `PipelineState` dict | Seed graph/agent tests |
| `valid_module_md` | 9-section module >2000 chars | Pass all `module_checks` |
| `valid_script` | 400-word script with contractions + `?` | Pass all `script_checks` |
| `valid_ppt_single` | JSON str for one topic slide | Pass all `ppt_checks` |
| `valid_ppt_full` | JSON str for full presentation | Pass all `ppt_checks` |
| `single_slide_pdf` | Path to temp single-page PDF | `extract_text` tests |
| `three_slide_pdfs` | Paths to 3 temp PDFs | Multi-file tests |
| `temp_chroma_dir` | Temp dir path | Isolated ChromaDB tests |

### Advanced Testing Techniques

=== "Property-Based (Hypothesis)"

    The structural check pure functions are tested with `hypothesis`, which generates thousands of edge cases automatically:

    ```python
    from hypothesis import given, strategies as st

    @given(st.text(max_size=1999))
    def test_any_string_shorter_than_2000_fails_min_length(self, text):
        from backend.evals.structural.module_checks import min_length
        assert not min_length(text)

    @given(st.text())
    def test_sanitize_never_contains_bad_control_chars(self, text):
        from backend.pipeline.agent_ingest import _sanitize
        result = _sanitize(text)
        for char in result:
            cp = ord(char)
            assert not (0x00 <= cp <= 0x08)
            assert cp != 0x7F
    ```

=== "Snapshot Tests (Syrupy)"

    Schema stability for `EvalResult` and `ComparisonResult` is verified with syrupy snapshots. If field names change, the test fails immediately:

    ```python
    def test_eval_result_fields_stable(self, snapshot):
        from backend.evals.datasets.schema import EvalResult
        field_names = sorted(EvalResult.model_fields.keys())
        assert field_names == snapshot  # compared to .ambr golden file
    ```

    Snapshots are stored in `backend/tests/__snapshots__/`. Run `--snapshot-update` once after an intentional schema change to update the golden file.

=== "LangGraph Graph Tests"

    The compiled pipeline graph is tested by patching all three agent nodes before calling `build_pipeline()`:

    ```python
    def test_pipeline_routes_through_all_three_nodes(self, base_pipeline_state):
        from backend.pipeline.graph import build_pipeline

        with (
            patch("backend.pipeline.graph.ingest_node") as mock_ingest,
            patch("backend.pipeline.graph.research_node") as mock_research,
            patch("backend.pipeline.graph.generate_node") as mock_generate,
        ):
            mock_ingest.return_value = {"topics": [...], "current_stage": "ingested"}
            mock_research.return_value = {"gap_summary": [], "current_stage": "researched"}
            mock_generate.return_value = {"pdf_path": "/tmp/out.pdf", "current_stage": "complete"}

            pipeline = build_pipeline()
            result = pipeline.invoke(base_pipeline_state)

        mock_ingest.assert_called_once()
        mock_research.assert_called_once()
        mock_generate.assert_called_once()
    ```

=== "sys.modules Stubbing (Kokoro)"

    `tts_engine.py` uses `soundfile`, `kokoro`, and `moviepy` which are not installed in dev/CI. Tests stub them via `sys.modules` before import:

    ```python
    import sys
    import types

    # Stub before import so the module loads without the real package
    sys.modules["soundfile"] = types.ModuleType("soundfile")
    sys.modules["kokoro"] = types.ModuleType("kokoro")

    from backend.services.tts_engine import synthesize
    ```

=== "GCS / GPU Client Mocking"

    `gcs_client.py` and `gpu_client.py` use `google.cloud.storage` and `requests` which call external services. Tests patch them at the module level:

    ```python
    from unittest.mock import MagicMock, patch

    @patch("backend.services.gcs_client.storage")
    def test_upload_job_inputs_returns_gcs_prefix(self, mock_storage):
        mock_bucket = MagicMock()
        mock_storage.Client.return_value.bucket.return_value = mock_bucket
        gcs = GCSVideoClient(bucket_name="test-bucket")
        prefix = gcs.upload_job_inputs("job123", ["/tmp/slide_01.png"], {"topics": []})
        assert prefix == "gs://test-bucket/job123"
    ```

---

## What the Tests Catch

| Category | Covered |
|----------|---------|
| All pure-function logic (structural checks, math, helpers) | Yes — full coverage + property-based |
| Every March 2026 bug fix | Yes — 21 dedicated regression tests |
| Schema stability (`EvalResult`, `ComparisonResult`) | Yes — Syrupy snapshots |
| LangGraph node wiring and state flow | Yes — Graph integration tests |
| All three agent nodes (happy path + failure paths) | Yes — With full mock isolation |
| `get_llm()` tier routing and silent fallback | Yes |
| Tavily `search()` happy path, empty results, errors | Yes |
| All FastAPI endpoints | Yes — Including auth flows |
| `[SLIDE N]` script parsing edge cases | Yes — 10 tests in `test_script_parser.py` |
| Kokoro TTS wrapper (`synthesize`, `synthesize_segments`) | Yes — 10 tests with stubbed soundfile |
| Kokoro two-phase video pipeline (TTS + parallel compose), shared engine, empty slide guard | Yes — 11 tests in `test_video_builder.py` |
| `export_slides_as_images()` PDF and PPTX paths | Yes — 6 tests in `test_file_parser.py` |
| PPTX upload magic byte validation | Yes — 6 tests in `frontend/tests/test_api.py` |
| Video UI (Kokoro TTS checkbox, warning box) | Yes — 4 tests in `frontend/tests/test_api.py` |
| Progress bar stage weights (including Video=25%) | Yes — Updated `test_progress_capture.py` |
| Stage-aware ETA with time budgets | Yes — 7 tests in `test_progress_capture.py` |
| Video provider validation: missing HeyGen/Synthesia keys, unknown provider | Yes — `test_run_pipeline.py` |
| GCS upload/download/cleanup with mocked `google.cloud.storage` | Yes — 12 tests in `test_gcs_client.py` |
| GPU client submit, poll (complete/error/timeout), identity token, health check | Yes — 12 tests in `test_gpu_client.py` |
| `_build_videos_dispatch()` GPU path and local fallback | Yes — 8 tests in `test_agent_generate_dispatch.py` |
| GPU service worker lifecycle (download, TTS, encode, upload) | Yes — 15 tests in `gpu_service/tests/test_worker.py` |
| GPU service FastAPI endpoints | Yes — 10 tests in `gpu_service/tests/test_app.py` |

## Known Gaps

| Gap | Mitigation |
|-----|------------|
| LLM output quality (all LLMs mocked) | Use `python -m backend.evals.cli run` (L2 judge) |
| True end-to-end integration across all 3 agents | Graph integration tests cover routing; agent tests cover logic |
| Concurrent execution safety | `ThreadPoolExecutor` paths are exercised, race conditions are not stress-tested |
| Binary output quality (PPT, video) | `ppt_builder` and `video_builder` are mocked in agent tests |
| External API breakage (HeyGen, OpenAI) | Caught by runtime monitoring, not unit tests |
| Real Kokoro TTS audio quality | E2E test with real Kokoro deps required (see T-011 — complete) |
| Real GCS/GPU service integration | Covered by mocked unit tests; E2E requires a deployed GPU service |

---

## Adding New Tests

### For a new structural check function

Add to `test_structural_checks.py` following the existing class pattern. No mocking needed — these are pure functions.

### For a new agent helper

Add to `test_pipeline_agents.py`. Mock any external calls (`ChromaStore`, `get_llm`, `search`, `extract_text`) via `unittest.mock.patch` at the import site in the agent module.

### For a new API endpoint

Add to `frontend/tests/test_api.py`. Use the existing `client` fixture (FastAPI `TestClient`).

### For a new schema field

After adding the field, run:

```bash
python3 -m pytest backend/tests/test_eval_harness.py::TestEvalResultSnapshot \
  --snapshot-update
```

This regenerates the `.ambr` golden file to include the new field. Commit both the code change and the updated snapshot.

### For a service with heavy optional dependencies

Use `sys.modules` stubbing (see Kokoro technique above) rather than `unittest.mock.patch` so the module loads cleanly without the optional package being installed in dev/CI.
