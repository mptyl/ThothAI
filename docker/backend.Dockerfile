# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# === MULTI-STAGE BUILD FOR BACKEND ===

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

# Install uv for fast package installation
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
    DOCKER_ENV=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    curl \
    cron \
    unixodbc \
    freetds-bin \
    libmariadb3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application code
COPY . .

# Ensure scripts are executable
RUN chmod +x /app/scripts/*.sh || true

# Create necessary directories including secrets
RUN mkdir -p /app/logs /app/exports /app/data /vol/static /vol/media /vol/secrets \
    && chmod 755 /app/logs /app/exports /app/data /vol/static /vol/media \
    && chmod 700 /vol/secrets

# Collect static files to the volume mount point
RUN python manage.py collectstatic --noinput --clear || true

# Setup cron for scheduled tasks
COPY scripts/crontab /etc/cron.d/thoth-cron
RUN chmod 0644 /etc/cron.d/thoth-cron \
    && crontab /etc/cron.d/thoth-cron \
    && touch /var/log/cron.log

# Copy entrypoint script
COPY entrypoint-backend.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8000/admin/login/ || exit 1

# Use custom entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Start script
COPY scripts/start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]