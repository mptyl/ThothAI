# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

# === SINGLE-STAGE BUILD FOR BACKEND ===

FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_ENV=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Ensure MariaDB build tools can find the config utility
    MARIADB_CONFIG="/usr/bin/mariadb_config"

WORKDIR /app

# Install build and runtime dependencies
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    curl \
    gnupg \
    pkg-config \
    build-essential \
    python3-dev \
    libssl-dev \
    # Helper for MariaDB/MySQL build tools (mariadb_config)
    libmariadb-dev \
    libmariadb-dev-compat \
    # Helper for SQL Server / ODBC
    unixodbc \
    unixodbc-dev \
    tdsodbc \
    # Other utilities
    cron \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Rust via rustup (for fastuuid compilation - requires newer Cargo)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && . "$HOME/.cargo/env" \
    && echo 'source $HOME/.cargo/env' >> ~/.bashrc
ENV PATH="/root/.cargo/bin:${PATH}"

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
# Use base pyproject.toml - all database drivers are included
# Runtime filtering via ENABLED_DATABASES controls which are available
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/uv.lock ./

# Copy application code (before installing dependencies to use cache better)
# But exclude .venv if it exists locally
COPY backend/ .
RUN rm -rf /app/.venv || true

# Install Python packages in the container
# This creates a fresh .venv with all dependencies
# Include ALL optional database drivers for maximum image portability
# Runtime filtering via ENABLED_DATABASES env var controls which are actually available
RUN uv sync --frozen --extra mariadb --extra sqlserver --extra all-databases

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
