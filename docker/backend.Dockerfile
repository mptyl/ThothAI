# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# === SINGLE-STAGE BUILD FOR BACKEND ===

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_ENV=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install build and runtime dependencies
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    curl \
    build-essential \
    cron \
    unixodbc \
    freetds-bin \
    libmariadb3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package installation
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && chmod +x /usr/local/bin/uv

# Copy dependency files first (for better caching)
# Use the merged pyproject.toml that includes database driver dependencies
COPY backend/pyproject.toml.merged ./pyproject.toml
COPY backend/uv.lock ./

# Copy application code (before installing dependencies to use cache better)
# But exclude .venv if it exists locally
COPY backend/ .
RUN rm -rf /app/.venv

# Install Python packages in the container
# This creates a fresh .venv with all dependencies
RUN uv sync --frozen

# Copy data directory to temporary location for initialization
# This will be copied to the volume on first run by init-shared-data.sh
COPY data/ /app/data_temp/

# Copy setup CSV files for initial data loading
COPY setup_csv/ /setup_csv/

# Ensure scripts are executable
RUN chmod +x /app/scripts/*.sh || true

# Create necessary directories including secrets
# Note: /app/data will be mounted from host, don't create it here
RUN mkdir -p /app/logs /app/exports /vol/static /vol/media /vol/secrets \
    && chmod 755 /app/logs /app/exports /vol/static /vol/media \
    && chmod 700 /vol/secrets

# Collect static files to the volume mount point
RUN /app/.venv/bin/python manage.py collectstatic --noinput --clear || true

# Setup cron for scheduled tasks
COPY backend/scripts/crontab /etc/cron.d/thoth-cron
RUN chmod 0644 /etc/cron.d/thoth-cron \
    && crontab /etc/cron.d/thoth-cron \
    && touch /var/log/cron.log

# Copy entrypoint script
COPY backend/entrypoint-backend.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8000/admin/login/ || exit 1

# Use custom entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Start script
COPY backend/scripts/start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]