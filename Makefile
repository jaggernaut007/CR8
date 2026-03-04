.PHONY: install test run clean serve dev docker-build docker-run docs-serve docs-build docs-deploy lint lint-fix

PYTHON := .venv/bin/python

install:
	python3 -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -v

run:
	$(PYTHON) -m backend.run_pipeline $(ARGS)

serve:
	cd "$(CURDIR)" && $(PYTHON) -m uvicorn frontend.app:app --reload --port 8080

dev:
	cd "$(CURDIR)" && $(PYTHON) -m uvicorn frontend.app:app --reload --host 0.0.0.0 --port 8080

docker-build:
	docker build -t cr8-pipeline .

docker-run:
	docker run -p 8080:8080 --env-file .env cr8-pipeline

clean:
	rm -rf chroma_db/ outputs/ __pycache__ backend/__pycache__ .pytest_cache

docs-serve:
	$(PYTHON) -m mkdocs serve --dev-addr 0.0.0.0:8000

docs-build:
	$(PYTHON) -m mkdocs build --strict

docs-deploy:
	$(PYTHON) -m mkdocs gh-deploy --force

lint:
	$(PYTHON) -m ruff check .

lint-fix:
	$(PYTHON) -m ruff check . --fix
