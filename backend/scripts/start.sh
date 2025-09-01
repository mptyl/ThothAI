#!/bin/bash

# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

set -e

echo "=== Starting Thoth Application ==="

# Load secrets from Docker volume if available
if [ -f "/secrets/django_secret_key" ]; then
    export SECRET_KEY=$(cat /secrets/django_secret_key)
    echo "SECRET_KEY loaded from Docker secrets volume"
fi

if [ -f "/secrets/django_api_key" ]; then
    export DJANGO_API_KEY=$(cat /secrets/django_api_key)
    echo "DJANGO_API_KEY loaded from Docker secrets volume"
fi

# Generate or load secrets if in Docker with auto-generation enabled
if [ "$AUTO_GENERATE_SECRETS" = "true" ] && [ -f "/app/scripts/generate-secrets.sh" ]; then
    echo "Loading/generating secrets..."
    . /app/scripts/generate-secrets.sh
fi

# Activate virtual environment
export PATH="/app/.venv/bin:$PATH"

# Ensure backend database directory exists
mkdir -p /app/backend_db

# Check SQLite database
echo "Checking SQLite database..."
/app/.venv/bin/python -c "
import os
import sqlite3
from pathlib import Path

# Get database path from environment
db_path = os.environ.get('DB_NAME_DOCKER', '/app/backend_db/db.sqlite3')
db_dir = os.path.dirname(db_path)

# Create directory if it doesn't exist
Path(db_dir).mkdir(parents=True, exist_ok=True)

# Create database file if it doesn't exist
if not os.path.exists(db_path):
    print(f'Creating new SQLite database at {db_path}')
    conn = sqlite3.connect(db_path)
    conn.close()
else:
    print(f'SQLite database found at {db_path}')

# Verify we can connect
try:
    conn = sqlite3.connect(db_path)
    conn.execute('SELECT 1')
    conn.close()
    print('Database is ready!')
except Exception as e:
    print(f'Database error: {e}')
    exit(1)
"

echo "Running makemigrations..."
/app/.venv/bin/python manage.py makemigrations

echo "Running migrate..."
/app/.venv/bin/python manage.py migrate

# Create cache table if it doesn't exist
echo "Creating cache table..."
/app/.venv/bin/python manage.py createcachetable || echo "Cache table already exists"

# Check migration status for debugging
echo "Checking migration status..."
/app/.venv/bin/python manage.py showmigrations thoth_core

# Create initial users from config.yml.local if available
echo "Creating initial users..."
if [ -f "/app/config.yml.local" ]; then
    echo "Loading user configuration from config.yml.local..."
    
    # Extract admin user details from config
    ADMIN_USERNAME=$(/app/.venv/bin/python -c "
import yaml
try:
    with open('/app/config.yml.local', 'r') as f:
        config = yaml.safe_load(f)
        print(config.get('admin', {}).get('username', 'admin'))
except:
    print('admin')
")
    
    ADMIN_EMAIL=$(/app/.venv/bin/python -c "
import yaml
try:
    with open('/app/config.yml.local', 'r') as f:
        config = yaml.safe_load(f)
        email = config.get('admin', {}).get('email', '')
        print(email if email else 'admin@example.com')
except:
    print('admin@example.com')
")
    
    ADMIN_PASSWORD=$(/app/.venv/bin/python -c "
import yaml
try:
    with open('/app/config.yml.local', 'r') as f:
        config = yaml.safe_load(f)
        print(config.get('admin', {}).get('password', 'admin123'))
except:
    print('admin123')
")
    
    # Extract demo user details from config
    DEMO_USERNAME=$(/app/.venv/bin/python -c "
import yaml
try:
    with open('/app/config.yml.local', 'r') as f:
        config = yaml.safe_load(f)
        print(config.get('demo', {}).get('username', 'demo'))
except:
    print('demo')
")
    
    DEMO_EMAIL=$(/app/.venv/bin/python -c "
import yaml
try:
    with open('/app/config.yml.local', 'r') as f:
        config = yaml.safe_load(f)
        email = config.get('demo', {}).get('email', '')
        print(email if email else 'demo@example.com')
except:
    print('demo@example.com')
")
    
    DEMO_PASSWORD=$(/app/.venv/bin/python -c "
import yaml
try:
    with open('/app/config.yml.local', 'r') as f:
        config = yaml.safe_load(f)
        print(config.get('demo', {}).get('password', 'demo1234'))
except:
    print('demo1234')
")
    
    # Create admin superuser
    echo "Creating admin superuser..."
    DJANGO_SUPERUSER_USERNAME="$ADMIN_USERNAME" \
    DJANGO_SUPERUSER_EMAIL="$ADMIN_EMAIL" \
    DJANGO_SUPERUSER_PASSWORD="$ADMIN_PASSWORD" \
    /app/.venv/bin/python manage.py createsuperuser --noinput 2>/dev/null || echo "Admin user '$ADMIN_USERNAME' already exists"
    
    # Create demo superuser
    echo "Creating demo superuser..."
    DJANGO_SUPERUSER_USERNAME="$DEMO_USERNAME" \
    DJANGO_SUPERUSER_EMAIL="$DEMO_EMAIL" \
    DJANGO_SUPERUSER_PASSWORD="$DEMO_PASSWORD" \
    /app/.venv/bin/python manage.py createsuperuser --noinput 2>/dev/null || echo "Demo user '$DEMO_USERNAME' already exists"
    
    echo "User creation completed."
else
    echo "config.yml.local not found, skipping user creation"
fi

echo "Running collectstatic..."
/app/.venv/bin/python manage.py collectstatic --noinput
echo "Collectstatic finished."

echo "Startup script completed successfully."

# Start Django server
echo "Starting Django server..."
echo "DEBUG: DJANGO_API_KEY value is: ${DJANGO_API_KEY:0:20}..."
echo "DEBUG: SECRET_KEY value is: ${SECRET_KEY:0:20}..."

# Ensure variables are exported to the environment
export DJANGO_API_KEY
export SECRET_KEY

# Start Django with environment variables available
exec /app/.venv/bin/python manage.py runserver 0.0.0.0:8000
