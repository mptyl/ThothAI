#!/bin/bash

# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Timer
START_TIME=$(date +%s)

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}ERROR: Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
}

# Function to check network and volumes
check_network() {
    if ! docker network ls | grep -q "thothnet"; then
        docker network create thothnet > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo -e "${RED}ERROR: Failed to create thothnet network${NC}"
            exit 1
        fi
    fi
    
    # Check shared volume (used with backend)
    if ! docker volume ls | grep -q "thoth-shared-data"; then
        docker volume create thoth-shared-data > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo -e "${RED}ERROR: Failed to create thoth-shared-data volume${NC}"
            exit 1
        fi
    fi
    
    # Check UI cache volume for universal build
    if [ "$USE_UNIVERSAL" == true ] && ! docker volume ls | grep -q "thoth-ui-cache"; then
        docker volume create thoth-ui-cache > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo -e "${YELLOW}WARNING: Failed to create thoth-ui-cache volume${NC}"
        fi
    fi
}

# Function to check environment files
check_env_files() {
    if [ ! -f ".env.docker" ]; then
        if [ -f ".env.docker.template" ]; then
            cp .env.docker.template .env.docker
            echo -e "${YELLOW}WARNING: Created .env.docker from template - please edit to configure your environment variables${NC}"
        else
            echo -e "${RED}ERROR: .env.docker.template not found${NC}"
            exit 1
        fi
    fi
}

# Function to build images
build_images() {
    # Use BuildKit for better caching
    export DOCKER_BUILDKIT=1
    
    # Parse build arguments
    BUILD_ARGS=""
    NO_CACHE=""
    SPECIFIC_SERVICE=""
    USE_UNIVERSAL=true  # Always use universal build
    COMPOSE_FILE="docker-compose.yml"
    
    for arg in "$@"; do
        case $arg in
            --no-cache)
                NO_CACHE="--no-cache"
                ;;
            --ui-only)
                SPECIFIC_SERVICE="thoth-ui"
                ;;
            --sql-only)
                SPECIFIC_SERVICE="sql-generator"
                ;;
            --dev)
                BUILD_ARGS="--build-arg NODE_ENV=development"
                ;;
            *)
                ;;
        esac
    done
    
    # Build with docker-compose
    if [ -n "$SPECIFIC_SERVICE" ]; then
        docker-compose -f $COMPOSE_FILE build $NO_CACHE $BUILD_ARGS --progress=plain $SPECIFIC_SERVICE > /dev/null 2>&1
    else
        docker-compose -f $COMPOSE_FILE build $NO_CACHE $BUILD_ARGS --progress=plain > /dev/null 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        END_TIME=$(date +%s)
        BUILD_TIME=$((END_TIME - START_TIME))
        echo -e "${GREEN}Build completed successfully ($BUILD_TIME seconds)${NC}"
    else
        echo -e "${RED}ERROR: Build failed${NC}"
        echo -e "${YELLOW}Run with 'docker-compose -f $COMPOSE_FILE build' to see detailed error messages${NC}"
        exit 1
    fi
}

# Function to display build info
display_info() {
    # Removed - not needed for minimal output
    :
}

# Parse arguments to set USE_UNIVERSAL before other functions
USE_UNIVERSAL=true  # Always use universal build
COMPOSE_FILE="docker-compose.yml"

# Main execution
echo -e "${CYAN}Building Thoth UI...${NC}"

# Check prerequisites
check_docker
check_network
check_env_files

# Build images
build_images "$@"

# Start containers
docker-compose -f $COMPOSE_FILE up -d > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Services started successfully${NC}"
    echo ""
    echo "Access points:"
    echo "  - Thoth UI:       http://localhost:3001"
    echo "  - SQL Generator:  http://localhost:8005/docs"
else
    echo -e "${RED}ERROR: Failed to start services${NC}"
    echo "Check logs with: docker-compose -f $COMPOSE_FILE logs"
    exit 1
fi