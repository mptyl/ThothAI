#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

set -e

echo "[INFO] Setting up ThothAI Docker environment..."

# Create network if it doesn't exist
if ! docker network ls | grep -q thothnet; then
    echo "Creating Docker network 'thothnet'..."
    docker network create thothnet
else
    echo "Network 'thothnet' already exists"
fi

# Create volume if it doesn't exist
if ! docker volume ls | grep -q "^local.*thoth-shared-data$"; then
    echo "Creating Docker volume 'thoth-shared-data'..."
    docker volume create thoth-shared-data
else
    echo "Volume 'thoth-shared-data' already exists"
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs setup_csv qdrant_storage ../data_exchange

# Check if _env file exists
if [ ! -f "_env" ]; then
    echo "[WARNING] _env file not found!"
    echo "Please copy _env.template to _env and configure your API keys"
    exit 1
fi

# Copy dev_databases to Docker volume if they exist and volume is empty
if [ -d "data/dev_databases" ]; then
    echo "Checking if dev_databases need to be copied to Docker volume..."
    
    # Get the volume mount point
    VOLUME_PATH=$(docker volume inspect thoth-shared-data --format '{{ .Mountpoint }}' 2>/dev/null || echo "")
    
    if [ -n "$VOLUME_PATH" ]; then
        # Check if volume is empty or doesn't have dev_databases
        if [ ! -d "$VOLUME_PATH/dev_databases" ]; then
            echo "Copying dev_databases to Docker volume..."
            # Need sudo on Linux, but not on macOS/Windows Docker Desktop
            if [ "$(uname)" = "Linux" ]; then
                sudo cp -r data/dev_databases "$VOLUME_PATH/"
                sudo cp -r data/*.sqlite "$VOLUME_PATH/" 2>/dev/null || true
            else
                # On macOS/Windows, we need to use a temporary container to copy files
                echo "Using Docker container to copy files to volume..."
                docker run --rm -v $(pwd)/data:/source -v thoth-shared-data:/target alpine sh -c "cp -r /source/dev_databases /target/ 2>/dev/null && cp /source/*.sqlite /target/ 2>/dev/null || true"
            fi
            echo "dev_databases copied successfully!"
        else
            echo "dev_databases already exist in Docker volume"
        fi
    else
        echo "[WARNING] Could not access Docker volume directly. Files will be copied on first container run."
        echo "Using container method to copy files..."
        docker run --rm -v $(pwd)/data:/source -v thoth-shared-data:/target alpine sh -c "cp -r /source/dev_databases /target/ 2>/dev/null && cp /source/*.sqlite /target/ 2>/dev/null || true"
    fi
else
    echo "[INFO] No dev_databases found in ./data directory"
fi

echo "[SUCCESS] Docker setup complete!"
echo ""
echo "To start ThothAI, run:"
echo "  docker compose up --build"
echo ""
echo "Access the application at:"
echo "  http://localhost:8040/admin"