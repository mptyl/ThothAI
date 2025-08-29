# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# === MULTI-STAGE BUILD FOR SQL GENERATOR ===

# Stage 1: Builder
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Install build dependencies
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && chmod +x /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python packages
RUN uv sync --frozen --quiet

# Stage 2: Runtime
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_CONTAINER=true \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /vol/secrets \
    && chmod 755 /app/logs /app/data \
    && chmod 700 /vol/secrets

# Copy entrypoint script  
COPY entrypoint-sql-generator.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# Use custom entrypoint
ENTRYPOINT ["/entrypoint.sh"]