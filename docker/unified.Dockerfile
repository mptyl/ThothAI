# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# === UNIFIED THOTH DOCKER IMAGE ===
# Single image containing all services for easy deployment

FROM python:3.13-slim AS python-builder

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
    && mv /root/.local/bin/uv /usr/local/bin/uv

# Build backend virtual environment
WORKDIR /build/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --quiet

# Build SQL generator virtual environment
WORKDIR /build/sql-generator
COPY frontend/sql_generator/pyproject.toml frontend/sql_generator/uv.lock ./
RUN uv sync --frozen --quiet

# === Node.js Builder ===
FROM node:20-alpine AS node-builder

WORKDIR /build

# Build frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG NEXT_PUBLIC_DJANGO_SERVER=http://localhost:8040
ARG NEXT_PUBLIC_SQL_GENERATOR_URL=http://localhost:8005
ENV NEXT_PUBLIC_DJANGO_SERVER=$NEXT_PUBLIC_DJANGO_SERVER
ENV NEXT_PUBLIC_SQL_GENERATOR_URL=$NEXT_PUBLIC_SQL_GENERATOR_URL
RUN npm run build

# === Final Image ===
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    curl \
    nginx \
    supervisor \
    postgresql-client \
    nodejs \
    npm \
    cron \
    && curl -fsSL https://github.com/qdrant/qdrant/releases/download/v1.7.4/qdrant-x86_64-unknown-linux-musl.tar.gz | tar -xz -C /usr/local/bin/ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 thoth && \
    mkdir -p /app /data /logs /exports && \
    chown -R thoth:thoth /app /data /logs /exports

WORKDIR /app

# Copy Python environments
COPY --from=python-builder /build/backend/.venv /app/backend/.venv
COPY --from=python-builder /build/sql-generator/.venv /app/sql-generator/.venv

# Copy backend
COPY --chown=thoth:thoth backend/ /app/backend/

# Copy frontend
COPY --from=node-builder --chown=thoth:thoth /build/.next /app/frontend/.next
COPY --from=node-builder --chown=thoth:thoth /build/public /app/frontend/public
COPY --from=node-builder --chown=thoth:thoth /build/package*.json /app/frontend/
COPY --from=node-builder --chown=thoth:thoth /build/node_modules /app/frontend/node_modules

# Copy SQL generator
COPY --chown=thoth:thoth frontend/sql_generator/ /app/sql-generator/

# Copy configuration files
COPY --chown=thoth:thoth scripts/ /app/scripts/
COPY --chown=thoth:thoth docker/nginx.conf /etc/nginx/nginx.conf
COPY --chown=thoth:thoth docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Setup environment
ENV PATH="/app/backend/.venv/bin:/app/sql-generator/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    DOCKER_ENV=1

# Create startup script
RUN cat > /app/start-all.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting ThothAI Unified Container..."

# Start PostgreSQL (if not using external)
if [ -z "$POSTGRES_HOST" ]; then
    echo "Starting embedded PostgreSQL..."
    su - postgres -c "pg_ctl start -D /var/lib/postgresql/data"
    sleep 5
    su - postgres -c "createdb thoth || true"
fi

# Start Qdrant
echo "Starting Qdrant vector database..."
/usr/local/bin/qdrant --storage-path /data/qdrant &

# Wait for services
sleep 10

# Run Django migrations
echo "Running database migrations..."
cd /app/backend
python manage.py migrate --noinput

# Create superuser if needed
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@thoth.ai', 'admin')
END

# Collect static files
python manage.py collectstatic --noinput

# Start all services with supervisor
echo "Starting all services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
EOF

RUN chmod +x /app/start-all.sh

# Expose ports
EXPOSE 80 8040 3001 8005 6333

# Volumes
VOLUME ["/data", "/logs", "/exports"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Switch to app user
USER thoth

# Start command
CMD ["/app/start-all.sh"]