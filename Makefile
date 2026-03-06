.PHONY: install test test-fast run clean serve dev docker-build docker-run docs-serve docs-build docs-deploy lint lint-fix build-frontend e2e

install:
	uv sync --all-extras

test:
	uv run pytest -v

test-fast:
	uv run pytest -x -q --tb=short

test-parallel:
	uv run pytest -v -n auto

run:
	uv run python -m backend.run_pipeline $(ARGS)

serve:
	cd "$(CURDIR)" && uv run uvicorn frontend.app:app --reload --port 8080

dev:
	cd "$(CURDIR)" && uv run uvicorn frontend.app:app --reload --host 0.0.0.0 --port 8080

docker-build:
	docker build -t cr8-pipeline .

docker-run:
	docker run -p 8080:8080 --env-file .env cr8-pipeline

clean:
	rm -rf chroma_db/ outputs/ __pycache__ backend/__pycache__ .pytest_cache

docs-serve:
	uv run mkdocs serve --dev-addr 0.0.0.0:8000

docs-build:
	uv run mkdocs build --strict

docs-deploy:
	uv run mkdocs gh-deploy --force

lint:
	uv run ruff check .

lint-fix:
	uv run ruff check . --fix

build-frontend:
	cd frontend/react-app && npm ci && npm run build && rm -rf ../static && cp -r dist/ ../static/

e2e:
	uv run pytest frontend/tests/ -v -k "e2e or playwright" --tb=short
