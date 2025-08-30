#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

echo "Starting ThothAI Unified Container..."

# Initialize PostgreSQL if needed
if [ ! -d "/var/lib/postgresql/data" ]; then
    echo "Initializing PostgreSQL..."
    mkdir -p /var/lib/postgresql/data
    chown -R postgres:postgres /var/lib/postgresql
    su - postgres -c "/usr/lib/postgresql/*/bin/initdb -D /var/lib/postgresql/data"
fi

# Start PostgreSQL (if not using external)
if [ -z "$POSTGRES_HOST" ]; then
    echo "Starting embedded PostgreSQL..."
    su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl start -D /var/lib/postgresql/data"
    sleep 5
    su - postgres -c "createdb thoth 2>/dev/null || true"
    su - postgres -c "createuser thoth 2>/dev/null || true"
fi

# Start Qdrant
echo "Starting Qdrant vector database..."
mkdir -p /data/qdrant
/usr/local/bin/qdrant --storage-path /data/qdrant &

# Wait for services
sleep 10

# Setup Django
echo "Setting up Django..."
cd /app/backend

# Activate virtual environment and run migrations
. /app/backend/.venv/bin/activate

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser if needed
python manage.py shell << PYTHON
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@thoth.ai', 'admin')
    print("Superuser created")
else:
    print("Superuser already exists")
PYTHON

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start all services with supervisor
echo "Starting all services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf