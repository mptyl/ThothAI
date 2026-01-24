#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Start all ThothAI services locally
# Backend, Frontend, SQL Generator run natively
# Qdrant and Mermaid run in Docker with separate local storage

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting ThothAI Local Development Environment${NC}"
echo "================================================"

# --- CLI Arguments ---
DETACHED=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -d|--detach) DETACHED=true ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# --- Configuration ---
BACKEND_PORT=${BACKEND_PORT:-8040}
FRONTEND_PORT=${FRONTEND_PORT:-3040}
SQL_GENERATOR_PORT=${SQL_GENERATOR_PORT:-8020}
QDRANT_PORT=${QDRANT_PORT:-6333}
QDRANT_LOCAL_STORAGE="./qdrant_storage_local"

# --- Load .env.local ---
if [ -f .env.local ]; then
    echo "Loading configuration from .env.local..."
    set -a
    source .env.local
    set +a
else
    echo -e "${YELLOW}⚠ .env.local not found. Creating from template...${NC}"
    if [ -f .env.local.template ]; then
        cp .env.local.template .env.local
        echo "Created .env.local - please configure API keys before running again."
        exit 1
    else
        echo -e "${RED}✗ .env.local.template not found. Cannot continue.${NC}"
        exit 1
    fi
fi

# --- Port Management ---
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        return 1
    fi
    return 0
}

reclaim_ports() {
    echo -e "${BLUE}Ensuring ports are free...${NC}"
    local ports=("$BACKEND_PORT" "$FRONTEND_PORT" "$SQL_GENERATOR_PORT" "$QDRANT_PORT")
    for port in "${ports[@]}"; do
        local pid=$(lsof -ti:"$port")
        if [ -n "$pid" ]; then
            echo "  Port $port is occupied by PID $pid. Reclaiming..."
            kill -9 $pid 2>/dev/null || true
        fi
    done
}

# --- Cleanup function ---
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping all services...${NC}"
    
    # Kill background processes
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null && echo "  Stopped backend"
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null && echo "  Stopped frontend"
    [ -n "$SQL_GEN_PID" ] && kill $SQL_GEN_PID 2>/dev/null && echo "  Stopped sql-generator"
    
    # Stop local Qdrant container
    docker stop thoth-qdrant-local 2>/dev/null && echo "  Stopped qdrant-local"
    
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}
trap cleanup INT TERM

# --- Step 1: Stop conflicting Docker services and reclaim ports ---
echo ""
echo -e "${BLUE}Step 1: Stopping conflicting Docker containers and reclaiming ports...${NC}"
if check_docker; then
    docker stop thoth-backend thoth-frontend thoth-sql-generator thoth-proxy thoth-qdrant 2>/dev/null || true
    echo "  Docker containers stopped (if any were running)"
else
    echo -e "${YELLOW}  ⚠ Docker daemon not running. Skipping Docker container cleanup.${NC}"
fi
reclaim_ports
echo "  Ports reclaimed"

# --- Step 2: Keep Mermaid running ---
echo ""
echo -e "${BLUE}Step 2: Ensuring Mermaid service is running...${NC}"
if check_docker; then
    if ! docker ps --format '{{.Names}}' | grep -q 'thoth-mermaid-service'; then
        docker compose up -d mermaid-service
        echo "  Started mermaid-service"
    else
        echo "  mermaid-service already running"
    fi
else
    echo -e "${YELLOW}  ⚠ Docker daemon not running. Mermaid service will be unavailable.${NC}"
fi

# --- Step 3: Start local Qdrant with separate storage ---
echo ""
echo -e "${BLUE}Step 3: Starting Qdrant with local storage...${NC}"
if check_docker; then
    mkdir -p "$QDRANT_LOCAL_STORAGE"

    # Stop existing local qdrant if running
    docker stop thoth-qdrant-local 2>/dev/null || true
    docker rm thoth-qdrant-local 2>/dev/null || true

    # Start Qdrant with local storage
    docker run -d \
        --name thoth-qdrant-local \
        -p ${QDRANT_PORT}:6333 \
        -v "$(pwd)/${QDRANT_LOCAL_STORAGE}:/qdrant/storage" \
        qdrant/qdrant:latest

    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    echo "  Qdrant started on port ${QDRANT_PORT} with storage in ${QDRANT_LOCAL_STORAGE}"

    # Wait for Qdrant to be ready
    echo "  Waiting for Qdrant to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:${QDRANT_PORT}/ > /dev/null 2>&1; then
            echo "  Qdrant is ready"
            break
        fi
        sleep 1
    done
else
    echo -e "${RED}  ✗ Docker daemon not running. Qdrant is MANDATORY for ThothAI.${NC}"
    echo -e "${RED}    Please start Docker and try again.${NC}"
    # We exit here because Qdrant is essential
    exit 1
fi

# --- Step 4: Start Backend ---
echo ""
echo -e "${BLUE}Step 4: Starting Backend on port ${BACKEND_PORT}...${NC}"

# Check for venv (from project root)
if [ ! -d "backend/.venv" ]; then
    echo -e "${RED}✗ Backend .venv not found. Please create it first with 'cd backend && uv sync'.${NC}"
    exit 1
fi

# Define Python path for backend (execute from project root to keep ./data paths correct)
BACKEND_PYTHON="backend/.venv/bin/python"

# Run migrations if needed
$BACKEND_PYTHON backend/manage.py migrate --run-syncdb > /dev/null 2>&1 || true

# Ensure cache table exists
$BACKEND_PYTHON backend/manage.py createcachetable 2>/dev/null || true

# --- Check if initial setup is needed (same logic as Docker start.sh) ---
echo "  Checking if initial database setup is needed..."
WORKSPACE_COUNT=$($BACKEND_PYTHON -c "
import os
import sys
sys.path.insert(0, 'backend')
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()
from thoth_core.models import Workspace
count = Workspace.objects.count()
print(count)
" 2>/dev/null || echo "0")

if [ "$WORKSPACE_COUNT" = "0" ]; then
    echo ""
    echo -e "${YELLOW}=========================================="
    echo "No workspaces found. Performing initial setup..."
    echo -e "==========================================${NC}"
    
    # Clean database for fresh installation
    echo "  Cleaning database for fresh installation..."
    $BACKEND_PYTHON -c "
import os
import sys
sys.path.insert(0, 'backend')
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()
from django.contrib.auth.models import User, Group
from thoth_core.models import (
    Workspace, SqlDb, SqlTable, SqlColumn, Relationship,
    AiModel, BasicAiModel, Agent, Setting, VectorDb
)

print('  Cleaning existing data...')

try:
    # Clean workspaces and related data
    Workspace.objects.all().delete()
    print('    - Deleted all Workspaces')

    # Clean database structures
    Relationship.objects.all().delete()
    SqlColumn.objects.all().delete()
    SqlTable.objects.all().delete()
    SqlDb.objects.all().delete()
    print('    - Deleted all SQL database structures')

    # Clean AI configurations
    Agent.objects.all().delete()
    Setting.objects.all().delete()
    AiModel.objects.all().delete()
    BasicAiModel.objects.all().delete()
    print('    - Deleted all AI configurations')

    # Clean VectorDB
    VectorDb.objects.all().delete()
    print('    - Deleted all Vector databases')

    # Clean groups (but not users)
    Group.objects.all().delete()
    print('    - Deleted all groups')

    print('  Database cleaned for fresh installation')
except Exception as e:
    # If tables don't exist, this is fine during first startup
    print(f'  Skipped cleaning: tables may not exist yet ({e})')
"
    
    # Load all default configurations (groups, users, workspace, AI models, etc.)
    echo "  Loading default configurations from setup_csv..."
    $BACKEND_PYTHON backend/manage.py load_defaults --source local || echo "  Warning: Could not load defaults"
    
    # Set user passwords
    echo "  Configuring user passwords..."
    $BACKEND_PYTHON -c "
import os
import sys
sys.path.insert(0, 'backend')
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()
from django.contrib.auth.models import User

# Update admin password
admin_user = User.objects.filter(username='admin').first()
if admin_user:
    admin_user.set_password('admin123')
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()
    print('    - Password set for admin user')

# Update demo password
demo_user = User.objects.filter(username='demo').first()
if demo_user:
    demo_user.set_password('demo1234')
    demo_user.is_superuser = True
    demo_user.is_staff = True
    demo_user.save()
    print('    - Password set for demo user')
"
    
    # Link workspace demo to demo user
    echo "  Setting up demo workspace for demo user..."
    $BACKEND_PYTHON -c "
import os
import sys
sys.path.insert(0, 'backend')
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()
from django.contrib.auth.models import User
from thoth_core.models import Workspace

demo_user = User.objects.filter(username='demo').first()
if demo_user:
    workspace = Workspace.objects.filter(id=1).first()
    if workspace:
        workspace.users.add(demo_user)
        workspace.default_workspace.add(demo_user)
        workspace.save()
        print(f'    - Workspace \"{workspace.name}\" linked to demo user')
    else:
        print('    - Warning: Workspace with ID 1 not found')
else:
    print('    - Warning: Demo user not found')
"
    
    # Run AI-assisted operations for demo workspace (if API keys are configured)
    if [ -n "$OPENAI_API_KEY" ] || \
       [ -n "$ANTHROPIC_API_KEY" ] || \
       [ -n "$GEMINI_API_KEY" ] || \
       [ -n "$MISTRAL_API_KEY" ] || \
       [ -n "$DEEPSEEK_API_KEY" ] || \
       [ -n "$OPENROUTER_API_KEY" ]; then
        echo ""
        echo -e "${BLUE}  Running AI-assisted analysis for demo database...${NC}"
        
        # Generate database scope
        echo "    1. Generating database scope..."
        $BACKEND_PYTHON backend/manage.py generate_scope --workspace 1 2>&1 || echo "    Warning: Scope generation failed or skipped"
        
        # Generate database documentation  
        echo "    2. Generating database documentation..."
        $BACKEND_PYTHON backend/manage.py generate_documentation --workspace 1 2>&1 || echo "    Warning: Documentation generation failed or skipped"
        
        # Run GDPR scan
        echo "    3. Scanning for GDPR-sensitive data..."
        $BACKEND_PYTHON backend/manage.py scan_gdpr --workspace 1 2>&1 || echo "    Warning: GDPR scan failed or skipped"
        
        echo -e "${GREEN}  AI-assisted analysis completed.${NC}"
    else
        echo "  No AI provider API keys configured - skipping AI analysis."
    fi
    
    # Load evidence, Gold SQL and run preprocessing for demo workspace
    echo "  Loading evidence and Gold SQL for demo workspace..."
    $BACKEND_PYTHON -c "
import os
import sys
sys.path.insert(0, 'backend')
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()
import time
from thoth_core.models import Workspace

workspace = Workspace.objects.filter(id=1).first()
if not workspace:
    print('    - Warning: Workspace ID 1 not found, skipping preprocessing')
else:
    print(f'    - Processing workspace: {workspace.name}')
    
    try:
        from thoth_ai_backend.preprocessing.upload_evidence import upload_evidence_to_vectordb
        from thoth_ai_backend.preprocessing.upload_questions import upload_questions_to_vectordb
        from thoth_ai_backend.async_tasks import run_preprocessing_task
        
        # Load evidence
        print('    - Loading evidence...')
        try:
            successful, total = upload_evidence_to_vectordb(workspace_id=1)
            print(f'      Evidence loaded: {successful}/{total} items')
            time.sleep(2)
        except Exception as e:
            print(f'      Warning: Could not load evidence: {e}')
        
        # Load Gold SQL
        print('    - Loading Gold SQL questions...')
        try:
            successful, total = upload_questions_to_vectordb(workspace_id=1)
            print(f'      Gold SQL loaded: {successful}/{total} pairs')
            time.sleep(2)
        except Exception as e:
            print(f'      Warning: Could not load Gold SQL: {e}')
        
        # Run preprocessing
        print('    - Running preprocessing...')
        try:
            run_preprocessing_task(workspace_id=1)
            print('      Preprocessing task started successfully')
        except Exception as e:
            print(f'      Warning: Could not start preprocessing: {e}')
            
    except ImportError as e:
        print(f'    - Warning: Could not import preprocessing modules: {e}')
"
    
    echo ""
    echo -e "${GREEN}=========================================="
    echo "Initial setup completed!"
    echo -e "==========================================${NC}"
    
else
    echo "  Found $WORKSPACE_COUNT workspace(s). Database already initialized."
fi

# --- Step 4: Start Backend ---
echo ""
echo -e "${BLUE}Step 4: Starting Backend on port ${BACKEND_PORT}...${NC}"

if [ "$DETACHED" = "true" ]; then
    cd backend
    source .venv/bin/activate
    nohup ./.venv/bin/python manage.py runserver ${BACKEND_PORT} > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..
else
    cd backend
    source .venv/bin/activate
    ./.venv/bin/python manage.py runserver ${BACKEND_PORT} &
    BACKEND_PID=$!
    cd ..
fi

echo "  Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "  Waiting for Backend to be ready..."
for i in {1..60}; do
    if curl -s http://localhost:${BACKEND_PORT}/admin/login/ > /dev/null 2>&1; then
        echo "  Backend is ready"
        break
    fi
    sleep 1
done

# --- Step 5: Start SQL Generator ---
echo ""
echo -e "${BLUE}Step 5: Starting SQL Generator on port ${SQL_GENERATOR_PORT}...${NC}"
cd frontend/sql_generator

if [ ! -d ".venv" ]; then
    echo -e "${RED}✗ SQL Generator .venv not found. Please create it first with 'uv sync'.${NC}"
    exit 1
fi

source .venv/bin/activate

# Export environment for sql-generator
export PORT=${SQL_GENERATOR_PORT}
export DJANGO_SERVER=http://localhost:${BACKEND_PORT}
export VECTOR_DB_HOST=localhost
export VECTOR_DB_PORT=${QDRANT_PORT}

if [ "$DETACHED" = "true" ]; then
    nohup uv run python main.py > ../../logs/sql_generator.log 2>&1 &
    SQL_GEN_PID=$!
    cd ../..
else
    uv run python main.py &
    SQL_GEN_PID=$!
    cd ../..
fi

echo "  SQL Generator started (PID: $SQL_GEN_PID)"

# --- Step 6: Start Frontend ---
echo ""
echo -e "${BLUE}Step 6: Starting Frontend on port ${FRONTEND_PORT}...${NC}"
cd frontend

# Export environment for Next.js
export PORT=${FRONTEND_PORT}
export DJANGO_SERVER=http://localhost:${BACKEND_PORT}
export SQL_GENERATOR_URL=http://localhost:${SQL_GENERATOR_PORT}
export NEXT_PUBLIC_DJANGO_SERVER=http://localhost:${BACKEND_PORT}
export NEXT_PUBLIC_SQL_GENERATOR_URL=http://localhost:${SQL_GENERATOR_PORT}

if [ "$DETACHED" = "true" ]; then
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
else
    npm run dev &
    FRONTEND_PID=$!
    cd ..
fi

echo "  Frontend started (PID: $FRONTEND_PID)"

# --- Summary ---
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}ThothAI Local Development Environment Started${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Service URLs:"
echo "  Frontend:      http://localhost:${FRONTEND_PORT}"
echo "  Backend:       http://localhost:${BACKEND_PORT}"
echo "  SQL Generator: http://localhost:${SQL_GENERATOR_PORT}"
echo "  Qdrant:        http://localhost:${QDRANT_PORT}"
echo "  Mermaid:       http://localhost:8003"
echo ""
echo "Database: backend/db.sqlite3 (local)"
echo "Qdrant Storage: ${QDRANT_LOCAL_STORAGE}/"
echo ""

if [ "$DETACHED" = "true" ]; then
    echo -e "${GREEN}Services are running in the background.${NC}"
    echo "Logs are available in the ./logs directory:"
    echo "  - Backend:       ./logs/backend.log"
    echo "  - SQL Generator: ./logs/sql_generator.log"
    echo "  - Frontend:      ./logs/frontend.log"
    echo ""
    echo -e "${YELLOW}To stop the services, you can run: ./stop-all.sh${NC}"
    echo ""
    exit 0
fi

echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for all processes
wait
