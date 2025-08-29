#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

echo "🌍 Universal Build - Works on ALL architectures!"
echo "==============================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Detect architecture for info only
ARCH=$(uname -m)
echo -e "${CYAN}Your architecture: $ARCH${NC}"
echo -e "${GREEN}[SUCCESS] This build works on ALL architectures!${NC}"
echo ""

echo "Features:"
echo "  • No compilation needed"
echo "  • Uses pre-compiled wheels"
echo "  • Works on Intel, AMD, Apple Silicon, ARM"
echo "  • Expected time: 2-3 minutes (depends on network)"
echo ""

# Timer
START_TIME=$(date +%s)

# Check network and volumes
if ! docker network ls | grep -q "thothnet"; then
    docker network create thothnet
    echo "✓ Created network: thothnet"
fi

if ! docker volume ls | grep -q "thoth-shared-data"; then
    docker volume create thoth-shared-data
    echo "✓ Created volume: thoth-shared-data"
fi

echo -e "${YELLOW}Building universal image...${NC}"
echo ""

# Build
DOCKER_BUILDKIT=1 docker build \
    -f Dockerfile \
    -t thoth_be-app:latest \
    --progress=plain \
    .

if [ $? -eq 0 ]; then
    END_TIME=$(date +%s)
    BUILD_TIME=$((END_TIME - START_TIME))
    
    echo ""
    echo -e "${GREEN}[SUCCESS] Build completed in $BUILD_TIME seconds!${NC}"
    echo ""
    
    # Start containers
    echo "Starting containers..."
    docker-compose up -d
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}[SUCCESS] All services started!${NC}"
        echo ""
        docker-compose ps
        echo ""
        echo "🌐 Access points:"
        echo "  • Application: http://localhost:8040"
        echo "  • Admin panel: http://localhost:8040/admin"
        echo "  • Qdrant UI:   http://localhost:6333/dashboard"
    fi
else
    echo -e "${RED}[ERROR] Build failed${NC}"
    exit 1
fi