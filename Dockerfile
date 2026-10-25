# Owner: M2 — Docker: multi-stage build
# Stage 1: Builder — install dependencies into a virtual environment
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Create venv and install wheels
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Stage 2: Runtime — slim image with venv copied
FROM python:3.11-slim AS runtime

# Install runtime lib for LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy application code
COPY src/ src/
COPY api/ api/
COPY config.yaml params.yaml ./

# Copy bundled model if available (for fallback)
COPY models/ models/

# Set ownership
RUN chown -R appuser:appuser /app

USER appuser

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION=1.0.0 \
    MLFLOW_TRACKING_URI=http://mlflow:5000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
