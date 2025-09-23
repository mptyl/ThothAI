# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# === SINGLE-STAGE BUILD FOR BACKEND ===

FROM python:3.13-slim-bookworm

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
    unixodbc-dev \
    freetds-bin \
    freetds-dev \
    cargo \
    rustc \
    pkg-config \
    tdsodbc \
    libmariadb3 \
    libmariadb-dev \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft SQL Server ODBC drivers (17 + 18) for pyodbc compatibility when available
COPY docker/install-msodbc.sh /tmp/install-msodbc.sh
RUN /tmp/install-msodbc.sh \
    && rm -f /tmp/install-msodbc.sh \
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
RUN rm -rf /app/.venv || true

# Install Python packages in the container
# This creates a fresh .venv with all dependencies
# Include optional database drivers using --extra flags
RUN uv sync --frozen --extra mariadb --extra sqlserver

# Copy data directory to temporary location for initialization
# This will be copied to the volume on first run by init-shared-data.sh
COPY data/ /app/data_temp/

# Copy setup CSV files for initial data loading
COPY setup_csv/ /setup_csv/

# Ensure scripts are executable and normalized to LF (robust on Windows checkouts)
RUN if [ -d /app/scripts ]; then \
      find /app/scripts -type f -name '*.sh' -exec sed -i 's/\r$//' {} + -exec chmod +x {} +; \
    fi || true

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
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8000/admin/login/ || exit 1

# Use custom entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Start script
COPY backend/scripts/start.sh /start.sh
RUN sed -i 's/\r$//' /start.sh && chmod +x /start.sh

CMD ["/start.sh"]
