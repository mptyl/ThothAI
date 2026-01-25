#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Clean ThothAI Docker environment
# Resets volumes (Internal DB, Qdrant) or schemas (External DB)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Cleaning ThothAI Docker Environment${NC}"
echo "====================================="

# --- Load .env.docker ---
if [ -f .env.docker ]; then
    echo "Loading configuration from .env.docker..."
    set -a
    source .env.docker
    set +a
else
    echo -e "${RED}✗ .env.docker not found. Cannot determine configuration.${NC}"
    exit 1
fi

# Standardize variables
DB_SCHEMA=${DB_SCHEMA:-thoth_db}
POSTGRES_INTERNAL=${POSTGRES_INTERNAL:-true}

# --- Step 1: Stop and Clean Docker Resources ---
echo -e "${BLUE}Step 1: Stopping services and removing volumes...${NC}"

# First, stop all containers explicitly
echo "  Stopping containers..."
docker compose stop

# Wait a moment for containers to fully stop
sleep 2

# We use 'docker compose down -v' to remove containers, networks, and VOLUMES.
# This effectively cleans Internal DB, Qdrant data, Redis (if any), etc.
if docker compose down -v; then
    echo "  Docker resources cleaned."
else
    echo -e "${RED}  Failed to clean Docker resources.${NC}"
    exit 1
fi

# Remove the internal PostgreSQL database volume if using internal DB
if [ "$POSTGRES_INTERNAL" = "true" ]; then
    echo "  Removing internal PostgreSQL database volume..."
    if docker volume rm thoth-postgres-data 2>/dev/null; then
        echo -e "${GREEN}  ✓ Internal PostgreSQL volume removed${NC}"
    else
        echo -e "${YELLOW}  ⚠ No internal PostgreSQL volume to remove (or already removed)${NC}"
    fi
fi

# Force remove the network if it still exists
echo "  Ensuring network removal..."
if docker network ls | grep -q "thoth-network"; then
    docker network rm thoth-network 2>/dev/null || echo -e "${YELLOW}  ⚠ Network cleanup will happen automatically${NC}"
fi

# --- Step 2: External Database Cleanup (Conditional) ---
if [ "$POSTGRES_INTERNAL" = "false" ]; then
    echo -e "${BLUE}Step 2: Cleaning External Database Schema...${NC}"
    
    # Check if necessary variables are set
    if [ -z "$DB_HOST" ]; then
        echo -e "${YELLOW}  ⚠ External DB configured (POSTGRES_INTERNAL=false) but DB_HOST not set. Skipping SQL cleanup.${NC}"
    else
        echo "  Targeting External DB at $DB_HOST ($DB_NAME)"
        
        # Construct Postgres connection string for use in container
        # Note: We use a temporary container to run psql, so we don't rely on local psql installation.
        # We need to make sure the network allows reaching the host if DB_HOST is host.docker.internal
        
        # If DB_HOST is host.docker.internal, we need to add host-gateway logic or run on host network if supported.
        # Simplest way for a quick utility script is to try running a small alpina/postgres container.
        
        # Prepare connection info
        export PGPASSWORD="${DB_PASSWORD:-thoth_pass}"
        USER="${DB_USER:-thoth_user}"
        DB="${DB_NAME:-thoth_db}"
        HOST="$DB_HOST"
        
        # SQL Command: Drop and recreate schemas
        SQL_CMD="DROP SCHEMA IF EXISTS thoth_schema CASCADE; DROP SCHEMA IF EXISTS $DB_SCHEMA CASCADE; CREATE SCHEMA $DB_SCHEMA;"
        
        echo "  Executing schema reset..."
        
        # We run a temporary postgres container to execute the command.
        # We mount the current directory just in case (not strictly needed for just a string command).
        # We use --network host to try to access external DBs easily, or we might need specific network config.
        # For 'host.docker.internal' to work on Linux without --network host might be tricky, but on Mac/Windows usually works if added.
        # To be safe and simple, let's try running a container attached to the host network (works best on Linux, on Mac host.docker.internal needs specific handling if not on host net).
        # Actually, since we are executing THIS script from the HOST, why not just try to run psql if installed? 
        # The requirement was "docker installation", user might not have psql locally.
        # Let's use a docker container.
        
        # Detect if we need special handling for host.docker.internal
        EXTRA_HOSTS=""
        if [[ "$HOST" == "host.docker.internal" ]]; then
            EXTRA_HOSTS="--add-host=host.docker.internal:host-gateway"
        fi
        
        docker run --rm $EXTRA_HOSTS \
            -e PGPASSWORD="$PGPASSWORD" \
            postgres:16-alpine \
            psql -h "$HOST" -p "${DB_PORT:-5432}" -U "$USER" -d "$DB" -c "$SQL_CMD"
            
        if [ $? -eq 0 ]; then
            echo "  External DB schema reset successfully."
        else
            echo -e "${RED}  Failed to reset External DB schema.${NC}"
            # We don't exit 1 here necessarily, maybe just warn? The docker part is done.
        fi
    fi
else
    echo -e "${BLUE}Step 2: Internal Database Cleaned via volume removal.${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Docker Environment reset complete!"
echo -e "==========================================${NC}"
