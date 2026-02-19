.PHONY: install test run clean serve dev

install:
	pip install -e ".[dev]"

test:
	pytest -v

run:
	python -m backend.run_pipeline $(ARGS)

serve:
	cd "$(CURDIR)" && uvicorn frontend.app:app --reload --port 8000

dev:
	cd "$(CURDIR)" && uvicorn frontend.app:app --reload --host 0.0.0.0 --port 8000

clean:
	rm -rf chroma_db/ outputs/ __pycache__ backend/__pycache__ .pytest_cache
