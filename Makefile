.PHONY: install test run clean

install:
	pip install -e ".[dev]"

test:
	pytest -v

run:
	python -m backend.run_pipeline $(ARGS)

clean:
	rm -rf chroma_db/ outputs/ __pycache__ backend/__pycache__ .pytest_cache
