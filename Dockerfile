# Multi-stage Docker build for Runpod Storage API

# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies and build wheel
RUN uv pip install --system --no-deps .
RUN uv build

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r runpod && useradd -r -g runpod runpod

# Copy application
WORKDIR /app
COPY --from=builder /app/dist/*.whl ./
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Install the built wheel
RUN pip install --no-deps *.whl && rm *.whl

# Change ownership
RUN chown -R runpod:runpod /app

# Switch to non-root user
USER runpod

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run the server
CMD ["runpod-storage-server", "--host", "0.0.0.0", "--port", "8000"]
