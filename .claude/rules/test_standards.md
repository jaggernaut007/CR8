---
description: CR8 test standards for pytest. Applied when editing test files. Covers naming, mocking, test techniques, and the definition of done for tests.
paths:
  - backend/tests/**/*.py
  - frontend/tests/**/*.py
---

# CR8 Test Standards

## Naming & Structure
- Test function naming: `test_[function_or_class]_[scenario]`
  - Examples: `test_ingest_agent_handles_empty_pdf`, `test_auth_rejects_invalid_token`
- Test files mirror source structure:
  - `backend/tests/test_services.py` → tests `backend/services/`
  - `backend/tests/test_pipeline_agents.py` → tests `backend/pipeline/agent_*.py`
  - `frontend/tests/test_api.py` → tests `frontend/app.py` endpoints

## Mocking (Critical)
- Mock ALL external API calls — the full 362-test suite must run with zero real API calls
- Use `unittest.mock.patch` or `pytest-mock` for OpenAI, Tavily, HeyGen, ChromaDB calls
- Never use real API keys in tests — if a test requires them, it belongs in a manual eval
- Check `backend/tests/test_services.py` for established mock patterns to follow

## Test Techniques
- **Property-based tests**: use `hypothesis` for data validation and edge cases
  - See `backend/tests/test_structural_checks.py` for examples
- **Snapshot regression tests**: use `syrupy` for output format regression
  - See `backend/tests/test_bug_fixes.py` for examples
- **Slow tests**: mark with `@pytest.mark.slow` for tests taking over 1 second

## Definition of Done for Tests
- Run `make test` and confirm all 362 tests pass before marking any task complete
- Read the test output via tool calls — never assume tests pass
- New features require new tests — no exceptions

## Running Tests
```bash
make test              # run full suite (362 tests)
pytest -v -k "keyword" # run specific tests
pytest --tb=short -q   # fast summary
```
