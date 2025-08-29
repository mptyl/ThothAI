#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}[WARNING] Docker Cleanup Tool for Thoth${NC}"
echo "=================================="
echo ""
echo "This will remove:"
echo "  • All Thoth Docker containers"
echo "  • All Thoth Docker images"
echo "  • All Thoth Docker volumes (optional)"
echo "  • All Thoth Docker networks"
echo ""
echo -e "${YELLOW}This simulates a first-time installation environment.${NC}"
echo ""

# Ask for confirmation
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo -e "${YELLOW}🛑 Stopping all Thoth containers...${NC}"
docker compose down 2>/dev/null
docker stop $(docker ps -a -q --filter "name=thoth") 2>/dev/null

echo -e "${YELLOW}🗑️  Removing Thoth containers...${NC}"
docker rm $(docker ps -a -q --filter "name=thoth") 2>/dev/null

echo -e "${YELLOW}🖼️  Removing Thoth images...${NC}"
# Remove app images
docker rmi thoth_be-app:latest 2>/dev/null
docker rmi thoth_be-db:latest 2>/dev/null
docker rmi thoth-be-proxy:v2 2>/dev/null
docker rmi thoth_ui-thoth-ui:latest 2>/dev/null
docker rmi thoth_ui-sql-generator:latest 2>/dev/null

# Also remove any dangling images related to Thoth
docker images | grep thoth | awk '{print $3}' | xargs docker rmi -f 2>/dev/null

echo -e "${YELLOW}🌐 Removing Thoth network...${NC}"
docker network rm thothnet 2>/dev/null

# Ask about volumes
echo ""
read -p "Do you also want to remove Docker volumes (database data)? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}💾 Removing Thoth volumes...${NC}"
    docker volume rm thoth_be_postgres-data 2>/dev/null
    docker volume rm thoth_be_static-data 2>/dev/null
    docker volume rm thoth-shared-data 2>/dev/null
    
    # Also remove local storage directories
    read -p "Remove local storage directories (qdrant_storage, logs, exports)? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}📁 Removing local storage directories...${NC}"
        rm -rf qdrant_storage 2>/dev/null
        rm -rf logs/* 2>/dev/null
        rm -rf exports/* 2>/dev/null
        echo "Local directories cleaned."
    fi
fi

# Optional: Remove Qdrant image
echo ""
read -p "Do you want to remove the Qdrant image as well? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🔍 Removing Qdrant image...${NC}"
    docker rmi qdrant/qdrant:latest 2>/dev/null
fi

# Clean buildx cache and builders
echo ""
read -p "Do you want to remove ALL Docker build cache (for truly clean builds)? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🗑️  Removing ALL Docker build cache...${NC}"
    
    # Remove buildx cache directories
    rm -rf /tmp/.buildx-cache* 2>/dev/null
    rm -rf /tmp/.docker-cache* 2>/dev/null
    rm -rf ~/.docker/buildx 2>/dev/null
    
    # Remove buildx builders
    docker buildx ls | grep -v "default" | awk '{print $1}' | xargs -r docker buildx rm 2>/dev/null
    
    # Nuclear option: Remove ALL Docker build cache
    docker builder prune -af --verbose 2>/dev/null
    docker system prune -af --volumes 2>/dev/null
    docker buildx prune -af --verbose 2>/dev/null
    
    # Remove any remaining build cache
    docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null
    
    echo "ALL Docker build cache removed!"
    echo ""
    echo -e "${RED}[WARNING] Next build will take 3-5 minutes (everything from scratch)${NC}"
fi

echo ""
echo -e "${GREEN}[SUCCESS] Cleanup completed!${NC}"
echo ""

# Show remaining Docker status
echo -e "${BLUE}📊 Current Docker status:${NC}"
echo ""
echo "Images:"
docker images | grep -E "thoth|qdrant" || echo "  No Thoth/Qdrant images found"
echo ""
echo "Containers:"
docker ps -a | grep thoth || echo "  No Thoth containers found"
echo ""
echo "Volumes:"
docker volume ls | grep thoth || echo "  No Thoth volumes found"
echo ""
echo "Networks:"
docker network ls | grep thoth || echo "  No Thoth networks found"

echo ""
echo -e "${GREEN}🎉 Environment is now clean!${NC}"
echo ""
echo "To simulate a first-time installation, run:"
echo "  1. ./setup-docker.sh  # Create network and volumes"
echo "  2. ./build-up.sh      # Build and start everything"
echo ""
echo "Or use the quick installer:"
echo "  ./install.sh"