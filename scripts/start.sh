#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

echo "Starting ThothAI Backend..."

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@thoth.ai', 'admin')
    print('Superuser created.')
else:
    print('Superuser already exists.')
END

# Load default data if needed
if [ -f "/app/setup_csv/users.csv" ]; then
    echo "Loading default data..."
    python manage.py shell << END
import os
os.system('python manage.py loaddata initial_data.json 2>/dev/null || true')
END
fi

# Start cron in background
service cron start

# Start Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --worker-class sync \
    --worker-tmp-dir /dev/shm \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    --log-level info \
    --timeout 120 \
    --graceful-timeout 30 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    Thoth.wsgi:application