#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# Quick wrapper to sync dev_databases to Docker volume without restarting containers
# This is useful during development to quickly add new databases

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load DB_ROOT_PATH from .env.local if present, and export it
if [ -f "$PROJECT_ROOT/.env.local" ]; then
    # shellcheck disable=SC1090
    set -a
    . "$PROJECT_ROOT/.env.local"
    set +a
    if [ -n "$DB_ROOT_PATH" ]; then
        echo "Using DB_ROOT_PATH from .env.local: $DB_ROOT_PATH"
    fi
fi

echo "=========================================="
echo "Quick Sync: dev_databases → Docker Volume"
echo "=========================================="

# Check if containers are running
if docker ps | grep -q "thoth-backend"; then
    echo "✓ Docker containers are running"
else
    echo "⚠ Docker containers are not running"
    echo "  You can still sync to the volume if it exists"
fi

# Call the main sync script with force flag if --force is passed
if [ "$1" == "--force" ]; then
    echo "Running sync in force mode (no confirmation)..."
    "$SCRIPT_DIR/sync-dev-databases.sh" --force
elif [ "$1" == "--dry-run" ]; then
    echo "Running sync in dry-run mode (preview only)..."
    "$SCRIPT_DIR/sync-dev-databases.sh" --dry-run
else
    # Interactive mode
    "$SCRIPT_DIR/sync-dev-databases.sh"
fi

echo ""
echo "=========================================="
echo "Sync operation completed"
echo "=========================================="
echo ""
echo "Usage:"
echo "  $0           # Interactive sync with confirmation"
echo "  $0 --force   # Sync without confirmation"
echo "  $0 --dry-run # Preview what will be synced"
echo ""
echo "Note: This sync is non-destructive and only adds new files."
echo "      Existing files in the volume are never overwritten."