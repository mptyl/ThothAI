#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# Script to sync dev_databases from local filesystem to Docker volume
# This performs a non-destructive sync: adds new files without overwriting existing ones

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
# Determine source directory. If DB_ROOT_PATH is provided (e.g., via .env.local), use it.
if [ -n "$DB_ROOT_PATH" ]; then
    SOURCE_DIR="$DB_ROOT_PATH/dev_databases"
else
    SOURCE_DIR="$PROJECT_ROOT/data/dev_databases"
fi
VOLUME_NAME="thoth-shared-data"

echo "======================================"
echo "Syncing dev_databases to Docker volume"
echo "======================================"
echo "Source: $SOURCE_DIR"
if [ -n "$DB_ROOT_PATH" ]; then
    echo "(DB_ROOT_PATH is set to: $DB_ROOT_PATH)"
fi
echo "Target Volume: $VOLUME_NAME"
echo ""

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "ERROR: Source directory does not exist: $SOURCE_DIR"
    exit 1
fi

# Check if Docker volume exists
if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    echo "ERROR: Docker volume '$VOLUME_NAME' does not exist"
    echo "Run 'docker-compose up' at least once to create the volume"
    exit 1
fi

# Function to sync using a temporary Alpine container
sync_with_docker() {
    echo "Starting sync operation..."
    
    # Use Alpine with rsync installed for the sync operation
    docker run --rm \
        -v "$SOURCE_DIR":/source:ro \
        -v "$VOLUME_NAME":/target \
        alpine:latest sh -c '
        # Install rsync if not available
        if ! command -v rsync >/dev/null 2>&1; then
            apk add --no-cache rsync >/dev/null 2>&1
        fi
        
        # Create target directory if it doesnt exist
        mkdir -p /target/dev_databases
        
        # Perform the sync
        # --archive: preserve permissions, timestamps, etc.
        # --ignore-existing: skip files that exist on receiver
        # --recursive: recurse into directories
        # --verbose: show what is being copied
        if command -v rsync >/dev/null 2>&1; then
            rsync -arv --ignore-existing /source/ /target/dev_databases/
        else
            # Fallback to cp if rsync is not available
            cp -rnv /source/* /target/dev_databases/ 2>/dev/null || true
        fi
        
        # Show summary
        echo ""
        echo "Sync completed. Current structure in volume:"
        find /target/dev_databases -type d | head -20
        echo ""
        echo "Total files in volume:"
        find /target/dev_databases -type f | wc -l
    '
}

# Function to show what will be synced (dry run)
show_changes() {
    echo "Checking for new files to sync..."
    
    docker run --rm \
        -v "$SOURCE_DIR":/source:ro \
        -v "$VOLUME_NAME":/target:ro \
        alpine:latest sh -c '
        echo "New directories that will be added:"
        for dir in $(find /source -type d); do
            target_dir="/target/dev_databases/${dir#/source/}"
            if [ ! -d "$target_dir" ]; then
                echo "  + $dir"
            fi
        done
        
        echo ""
        echo "New files that will be added:"
        for file in $(find /source -type f); do
            target_file="/target/dev_databases/${file#/source/}"
            if [ ! -f "$target_file" ]; then
                echo "  + ${file#/source/}"
            fi
        done
    '
}

# Main execution
if [ "$1" == "--dry-run" ]; then
    echo "DRY RUN MODE - No changes will be made"
    echo ""
    show_changes
else
    show_changes
    echo ""
    read -p "Do you want to proceed with the sync? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sync_with_docker
        echo ""
        echo "✓ Sync completed successfully"
    else
        echo "Sync cancelled"
        exit 0
    fi
fi

echo ""
echo "To run without confirmation, use: $0 --force"
echo "To see what would be synced, use: $0 --dry-run"

# Handle --force flag
if [ "$1" == "--force" ]; then
    sync_with_docker
    echo ""
    echo "✓ Sync completed successfully (forced)"
fi