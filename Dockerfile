# ---- Stage 1: Builder ----
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifest first for layer caching
COPY pyproject.toml ./
# Minimal source layout so `pip install .` can resolve the package
COPY backend/__init__.py backend/__init__.py

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .


# ---- Stage 2: Runtime ----
FROM python:3.11-slim AS runtime

# Runtime deps for pymupdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY pyproject.toml ./

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
