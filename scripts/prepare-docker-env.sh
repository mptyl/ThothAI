#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Script to prepare Docker environment after initial install

echo "Preparing Docker environment..."

# Check if config.yml.local exists
if [ ! -f "config.yml.local" ]; then
    echo "ERROR: config.yml.local not found!"
    echo "Please run ./install.sh first"
    exit 1
fi

# Create .env.docker if it doesn't exist
if [ ! -f ".env.docker" ]; then
    echo "Creating .env.docker from template..."
    
    if [ -f ".env.docker.example" ]; then
        cp .env.docker.example .env.docker
        echo "Created .env.docker from .env.docker.example"
    elif [ -f ".env.template" ]; then
        cp .env.template .env.docker
        echo "Created .env.docker from .env.template"
    else
        # Create a minimal .env.docker
        cat > .env.docker << EOF
# Docker environment variables
NODE_ENV=production
DJANGO_DEBUG=False
PYTHONUNBUFFERED=1
EOF
        echo "Created minimal .env.docker"
    fi
fi

# Fix line endings for shell scripts
if [ -f "./scripts/prepare-docker-build.sh" ]; then
    echo "Fixing line endings for shell scripts..."
    ./scripts/prepare-docker-build.sh
fi

# Create necessary directories
directories=("data_exchange" "logs" "backend/logs" "frontend/logs")
for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "Created directory: $dir"
    fi
done

echo ""
echo "Environment prepared!"
echo ""
echo "You can now run:"
echo "  docker-compose build"
echo "  docker-compose up"
echo ""
echo "Or use the shortcut:"
echo "  docker-compose up --build"