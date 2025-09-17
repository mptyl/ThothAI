# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# ===== UNIVERSAL BUILD - Works on ALL architectures =====
# No compilation, uses pre-built wheels for everything
# Works on: Intel/AMD (x86_64), Apple Silicon (ARM64), Raspberry Pi (ARM)

FROM python:3.13

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_ENV=1

WORKDIR /app

# Install ALL database system dependencies for maximum compatibility
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    cron \
    curl \
    gnupg \
    unixodbc \
    unixodbc-dev \
    freetds-dev \
    freetds-bin \
    libmariadb-dev \
    libmariadb-dev-compat \
    default-libmysqlclient-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update -qq \
    && ACCEPT_EULA=Y apt-get install -y -qq msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package installation
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && chmod +x /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python packages - uses pre-compiled wheels for ALL architectures!
# Include MariaDB and SQL Server support since system dependencies are installed
RUN uv sync --frozen --quiet --extra mariadb --extra sqlserver

# Copy application code
COPY . .

# Fix script permissions
RUN chmod +x /app/scripts/*.sh

CMD ["/app/scripts/start-with-cron.sh", "/usr/local/bin/uv", "run", "gunicorn", "--config", "gunicorn.conf.py", "Thoth.wsgi:application"]