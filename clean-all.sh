#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Clean ThothAI environment to first startup conditions
# Resets Postgres database and Qdrant storage

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Cleaning ThothAI Environment${NC}"
echo "============================="

# --- Load .env.local ---
if [ -f .env.local ]; then
    echo "Loading configuration from .env.local..."
    set -a
    source .env.local
    set +a
else
    echo -e "${RED}✗ .env.local not found. Nothing to clean based on config.${NC}"
    exit 1
fi

# Standardize variables
DB_SCHEMA=${DB_SCHEMA:-thoth_db}
QDRANT_LOCAL_STORAGE="./qdrant_storage_local"

# --- Step 1: Stop Services ---
echo -e "${BLUE}Step 1: Stopping all services...${NC}"
if docker info > /dev/null 2>&1; then
    docker stop thoth-db thoth-mermaid-service thoth-qdrant-local thoth-backend thoth-frontend thoth-sql-generator thoth-proxy thoth-qdrant 2>/dev/null || true
    docker rm thoth-mermaid-service 2>/dev/null || true
    echo "  Docker containers stopped and mermaid-service removed"
fi

# --- Step 2: Clean Postgres ---
echo -e "${BLUE}Step 2: Cleaning Postgres database...${NC}"
if [ -n "$DATABASE_URL" ]; then
    echo "  Using DATABASE_URL and schema $DB_SCHEMA"
    # We drop both thoth_schema and the target schema for thorough cleanup
    psql "$DATABASE_URL" -c "DROP SCHEMA IF EXISTS thoth_schema CASCADE; DROP SCHEMA IF EXISTS $DB_SCHEMA CASCADE; CREATE SCHEMA $DB_SCHEMA;"
    echo "  Postgres schema $DB_SCHEMA reset"
else
    echo -e "${YELLOW}  ⚠ DATABASE_URL not set. Skipping Postgres cleanup.${NC}"
fi

# --- Step 3: Clean Qdrant Local Storage ---
echo -e "${BLUE}Step 3: Cleaning Qdrant local storage...${NC}"
if [ -d "$QDRANT_LOCAL_STORAGE" ]; then
    rm -rf "$QDRANT_LOCAL_STORAGE"
    echo "  Deleted $QDRANT_LOCAL_STORAGE"
else
    echo "  $QDRANT_LOCAL_STORAGE not found"
fi

# --- Step 4: Clean SQLite (Optional fallback) ---
if [ -f "backend/db.sqlite3" ]; then
    echo -e "${BLUE}Step 4: Cleaning local SQLite...${NC}"
    rm -f "backend/db.sqlite3"
    echo "  Deleted backend/db.sqlite3"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Environment reset to first startup state!"
echo -e "==========================================${NC}"
