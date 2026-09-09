# SIH 2026 PS45 - Legal RAG Pipeline Dockerfile
# Multi-stage build for production deployment

# ============================================================
# BASE STAGE - Common dependencies
# ============================================================
FROM python:3.10-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements-prod.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt

# ============================================================
# BUILD STAGE - Copy application code
# ============================================================
FROM base as builder

# Copy application code
COPY . .

# Pre-download NLLB-200 model to avoid first-request latency
# (This runs during build if network is available)
# RUN python3 -c "from translation_service import get_translation_service; get_translation_service().load_models()" || true

# ============================================================
# RUNTIME STAGE - Final production image
# ============================================================
FROM python:3.10-slim as runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app /app

# Create directories with correct permissions
RUN mkdir -p /app/vector_db /app/logs /app/output && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    RAG_BASE_DIR=/app \
    RAG_VECTOR_DB_PATH=/app/vector_db \
    RAG_LOGS_DIR=/app/logs \
    RAG_OUTPUT_DIR=/app/output

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

# Default command (API server)
CMD ["gunicorn", "api.main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "180"]