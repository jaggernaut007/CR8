# ---- Stage 0: Frontend ----
FROM node:22-slim AS frontend

WORKDIR /app/frontend/react-app
COPY frontend/react-app/package.json frontend/react-app/package-lock.json ./
RUN npm ci
COPY frontend/react-app/ ./
RUN npm run build


# ---- Stage 1: Builder ----
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifest + lockfile first for layer caching
COPY pyproject.toml uv.lock ./
# Minimal source layout so uv can resolve the package
COPY backend/__init__.py backend/__init__.py

# Install without video extras (kokoro/torch/moviepy ~3.5GB) —
# video processing is offloaded to the GPU Cloud Run service.
RUN uv sync --frozen --no-dev --no-editable --no-extra video


# ---- Stage 2: Runtime ----
FROM python:3.11-slim AS runtime

# Runtime deps: pymupdf (libglib), PDF tools (poppler), LibreOffice (PPTX→PDF
# for slide image export — needed so the PPT carousel can show gap analysis
# slides without relying on the GPU service).
# Video deps (ffmpeg, espeak-ng, kokoro/torch) are NOT included — video
# processing is offloaded to dedicated GPU/CPU-video Cloud Run services.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsndfile1 \
    poppler-utils \
    libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    TOKENIZERS_PARALLELISM="false"

WORKDIR /app

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY pyproject.toml ./

# Copy built React SPA into frontend/static/ (enables SPA mode in frontend/app.py)
COPY --from=frontend /app/frontend/react-app/dist/ ./frontend/static/

# Create directories the app expects
RUN mkdir -p uploads outputs chroma_db

EXPOSE 8080

# Single gunicorn worker — the app uses in-memory state and blocks
# concurrent jobs, so multiple workers would break things.
# --timeout 3600 prevents the worker from being killed during long
# pipeline runs (5-15 min).  Cloud Run sets PORT=8080 by default.
CMD ["gunicorn", "frontend.app:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "1", \
     "--bind", "0.0.0.0:8080", \
     "--timeout", "3600", \
     "--keep-alive", "65", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
