#!/bin/bash

# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

set -e

# Set Django settings module
export DJANGO_SETTINGS_MODULE=Thoth.settings

# Set DB_ROOT_PATH for evidence and Gold SQL loading
export DB_ROOT_PATH=/app/data

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

# Check if initial setup is needed
echo "Checking if initial setup is needed..."
WORKSPACE_COUNT=$(/app/.venv/bin/python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()
from thoth_core.models import Workspace
count = Workspace.objects.count()
print(count)
" 2>/dev/null || echo "0")

if [ "$WORKSPACE_COUNT" = "0" ]; then
    echo "=========================================="
    echo "No workspaces found. Performing initial setup..."
    echo "=========================================="
    
    # Clean database for fresh installation
    echo "Cleaning database for fresh installation..."
    /app/.venv/bin/python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()
from django.contrib.auth.models import User, Group
from thoth_core.models import (
    Workspace, SqlDb, SqlTable, SqlColumn, Relationship,
    AiModel, BasicAiModel, Agent, Setting, VectorDb
)

print('Cleaning existing data...')

# Clean workspaces and related data
Workspace.objects.all().delete()
print('- Deleted all Workspaces')

# Clean database structures
Relationship.objects.all().delete()
SqlColumn.objects.all().delete()
SqlTable.objects.all().delete()
SqlDb.objects.all().delete()
print('- Deleted all SQL database structures')

# Clean AI configurations
Agent.objects.all().delete()
Setting.objects.all().delete()
AiModel.objects.all().delete()
BasicAiModel.objects.all().delete()
print('- Deleted all AI configurations')

# Clean VectorDB
VectorDb.objects.all().delete()
print('- Deleted all Vector databases')

# Clean profiles (if models exist)
# Note: UserProfile and GroupProfile models may not exist in this version

# Clean groups (but not users)
Group.objects.all().delete()
print('- Deleted all groups')

print('Database cleaned for fresh installation')
"
    
    # 1. Load groups from setup_csv
    echo "Loading groups from setup_csv..."
    /app/.venv/bin/python manage.py import_groups --source docker || echo "Warning: Could not load groups"
    
    # 2. Create initial users from config.yml.local if available
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
    
    # 3. Associate users with groups
    echo "Associating users with groups..."
    /app/.venv/bin/python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()
from django.contrib.auth.models import User, Group

# Associate admin with groups admin, editor, technical_user
admin_user = User.objects.filter(username='admin').first()
if admin_user:
    groups = Group.objects.filter(name__in=['admin', 'editor', 'technical_user'])
    if groups.exists():
        admin_user.groups.set(groups)
        print(f'Admin user associated with groups: {list(groups.values_list(\"name\", flat=True))}')
    else:
        print('Warning: Groups not found for admin user')
else:
    print('Warning: Admin user not found')

# Associate demo with groups editor and technical_user
demo_user = User.objects.filter(username='demo').first()
if demo_user:
    groups = Group.objects.filter(name__in=['editor', 'technical_user'])
    if groups.exists():
        demo_user.groups.set(groups)
        print(f'Demo user associated with groups: {list(groups.values_list(\"name\", flat=True))}')
    else:
        print('Warning: Groups not found for demo user')
else:
    print('Warning: Demo user not found')
"
    
    # 4. Load default configurations
    echo "Loading default configurations..."
    /app/.venv/bin/python manage.py load_defaults --source docker || echo "Warning: Could not load defaults"
    
    # 5. Link workspace demo to demo user
    echo "Setting up demo workspace for demo user..."
    /app/.venv/bin/python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()
from django.contrib.auth.models import User
from thoth_core.models import Workspace

demo_user = User.objects.filter(username='demo').first()
if demo_user:
    workspace = Workspace.objects.filter(id=1).first()
    if workspace:
        # Add workspace to user's available workspaces
        workspace.users.add(demo_user)
        # Set workspace as default for demo user
        workspace.default_workspace.add(demo_user)
        workspace.save()
        print(f'Workspace \"{workspace.name}\" (ID: 1) linked to demo user and set as default')
    else:
        print('Warning: Workspace with ID 1 not found')
else:
    print('Warning: Demo user not found')
"
    
    # 6. Run AI-assisted operations for demo workspace (if API keys are configured)
    echo ""
    echo "=========================================="
    echo "Checking for AI configuration..."
    echo "=========================================="
    
    # Check if any LLM API key is configured
    if [ -n "$OPENAI_API_KEY" ] || [ -n "$ANTHROPIC_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ] || [ -n "$MISTRAL_API_KEY" ] || [ -n "$DEEPSEEK_API_KEY" ]; then
        echo "AI provider configured. Running automated analysis for demo database..."
        echo ""
        
        # Generate database scope
        echo "1. Generating database scope..."
        /app/.venv/bin/python manage.py generate_scope --workspace 1 2>&1 || echo "Warning: Scope generation failed or skipped"
        echo ""
        
        # Generate database documentation  
        echo "2. Generating database documentation..."
        /app/.venv/bin/python manage.py generate_documentation --workspace 1 2>&1 || echo "Warning: Documentation generation failed or skipped"
        echo ""
        
        # Run GDPR scan
        echo "3. Scanning for GDPR-sensitive data..."
        /app/.venv/bin/python manage.py scan_gdpr --workspace 1 2>&1 || echo "Warning: GDPR scan failed or skipped"
        echo ""
        
        echo "=========================================="
        echo "AI-assisted analysis completed for demo workspace."
        echo "=========================================="
    else
        echo "No AI provider API keys configured."
        echo "Skipping automated scope, documentation, and GDPR scan."
        echo "To enable AI features, configure one of these environment variables:"
        echo "  - OPENAI_API_KEY"
        echo "  - ANTHROPIC_API_KEY" 
        echo "  - GOOGLE_API_KEY"
        echo "  - MISTRAL_API_KEY"
        echo "  - DEEPSEEK_API_KEY"
        echo "=========================================="
    fi
    
    # 6. Load evidence, Gold SQL and run preprocessing for demo workspace
    echo "Loading evidence, Gold SQL and running preprocessing for demo workspace..."
    /app/.venv/bin/python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()
import time
from thoth_core.models import Workspace

# Verify workspace exists
workspace = Workspace.objects.filter(id=1).first()
if not workspace:
    print('Warning: Workspace ID 1 not found, skipping preprocessing')
else:
    print(f'Processing workspace: {workspace.name}')
    
    # Import preprocessing modules
    try:
        from thoth_ai_backend.preprocessing.upload_evidence import upload_evidence_to_vectordb
        from thoth_ai_backend.preprocessing.upload_questions import upload_questions_to_vectordb
        from thoth_ai_backend.async_tasks import run_preprocessing_task
        
        # 1. Load evidence
        print('Loading evidence for workspace demo...')
        try:
            successful, total = upload_evidence_to_vectordb(workspace_id=1)
            print(f'Evidence loaded: {successful}/{total} items')
            time.sleep(2)  # Pause for stabilization
        except Exception as e:
            print(f'Warning: Could not load evidence: {e}')
        
        # 2. Load Gold SQL (questions/answers pairs)
        print('Loading Gold SQL questions for workspace demo...')
        try:
            successful, total = upload_questions_to_vectordb(workspace_id=1)
            print(f'Gold SQL loaded: {successful}/{total} pairs')
            time.sleep(2)  # Pause for stabilization
        except Exception as e:
            print(f'Warning: Could not load Gold SQL: {e}')
        
        # 3. Run preprocessing
        print('Running preprocessing for workspace demo...')
        try:
            run_preprocessing_task(workspace_id=1)
            print('Preprocessing task started successfully')
        except Exception as e:
            print(f'Warning: Could not start preprocessing: {e}')
            
    except ImportError as e:
        print(f'Warning: Could not import preprocessing modules: {e}')

print('')
print('==========================================')
print('Initial setup completed!')
print('==========================================')
"
    
else
    echo "Found $WORKSPACE_COUNT workspace(s). Skipping initial setup."
    echo "Database already initialized."
    
    # Still create users if they don't exist (for container restarts)
    echo "Checking users..."
    if [ -f "/app/config.yml.local" ]; then
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
        
        # Create admin superuser if not exists
        DJANGO_SUPERUSER_USERNAME="$ADMIN_USERNAME" \
        DJANGO_SUPERUSER_EMAIL="admin@example.com" \
        DJANGO_SUPERUSER_PASSWORD="admin123" \
        /app/.venv/bin/python manage.py createsuperuser --noinput 2>/dev/null || echo "Admin user '$ADMIN_USERNAME' already exists"
        
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
        
        # Create demo superuser if not exists
        DJANGO_SUPERUSER_USERNAME="$DEMO_USERNAME" \
        DJANGO_SUPERUSER_EMAIL="demo@example.com" \
        DJANGO_SUPERUSER_PASSWORD="demo1234" \
        /app/.venv/bin/python manage.py createsuperuser --noinput 2>/dev/null || echo "Demo user '$DEMO_USERNAME' already exists"
    fi
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

# Start Django with Gunicorn for production
echo "Starting Gunicorn production server..."

# Check if gunicorn is installed
if [ ! -f "/app/.venv/bin/gunicorn" ]; then
    echo "Gunicorn not found, installing..."
    /app/.venv/bin/pip install gunicorn
fi

# Start Gunicorn with environment variables available
exec /app/.venv/bin/gunicorn \
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
