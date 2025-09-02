# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# === SINGLE-STAGE BUILD FOR SQL GENERATOR ===

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_CONTAINER=true \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# Install runtime dependencies and uv
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && chmod +x /usr/local/bin/uv

# Copy dependency files first for better caching
# Use the merged pyproject.toml that includes database driver dependencies
COPY frontend/sql_generator/pyproject.toml.merged ./pyproject.toml
COPY frontend/sql_generator/uv.lock ./

# Copy application code (before installing dependencies to use cache better)
# .venv is excluded via .dockerignore
COPY frontend/sql_generator/ .

# Install Python packages using uv with system Python
# This creates a fresh .venv with all dependencies
RUN uv sync --frozen --no-cache

# Copy data directory into image (for reference/backup)
COPY data/ /app/data_static

# Create necessary directories
RUN mkdir -p /app/logs /app/data /vol/secrets \
    && chmod 755 /app/logs /app/data \
    && chmod 700 /vol/secrets

# Copy database files to the working data directory
# This ensures databases are available even if volume is empty
COPY data/dev_databases /app/data/dev_databases

# Copy entrypoint script
COPY frontend/sql_generator/entrypoint-sql-generator.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8020

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8020/health || exit 1

# Use custom entrypoint
ENTRYPOINT ["/entrypoint.sh"]