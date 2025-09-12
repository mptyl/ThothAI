# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# ===== UNIVERSAL BUILD - Works on ALL architectures =====
# No compilation, uses pre-built wheels for everything
# Works on: Intel/AMD (x86_64), Apple Silicon (ARM64), Raspberry Pi (ARM)

FROM python:3.13

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    DOCKER_CONTAINER=true

WORKDIR /app

# Install ALL database system dependencies for maximum compatibility
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
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

# Copy uv for fast package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python packages - uses pre-compiled wheels for ALL architectures!
# First sync, then upgrade thoth-dbmanager to fix the mariadb import issue
RUN uv sync --frozen && \
    uv pip install --upgrade "thoth-dbmanager[postgresql,sqlite]>=0.5.10"

# Copy application code
COPY . .

EXPOSE 8001

# Run with uv for consistency
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
