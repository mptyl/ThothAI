#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# Script for building and pushing Docker images to registry for Swarm deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    echo -e "${2}${1}${NC}"
}

# Function to show usage
show_usage() {
    print_color "Usage: $0 REGISTRY_URL VERSION [OPTIONS]" "$BLUE"
    print_color "" "$NC"
    print_color "Arguments:" "$YELLOW"
    print_color "  REGISTRY_URL    Docker registry URL (e.g.: registry.uni.com/tylconsulting/ThothAI)" "$NC"
    print_color "  VERSION         Image version (e.g.: 0.1, 1.0, latest)" "$NC"
    print_color "" "$NC"
    print_color "Options:" "$YELLOW"
    print_color "  --no-cache      Build without using cache" "$NC"
    print_color "  --push-only     Push only images (skip build)" "$NC"
    print_color "  --help          Show this message" "$NC"
    echo ""
    print_color "Example:" "$GREEN"
    print_color "  $0 registry.uni.com/tylconsulting/ThothAI 0.1" "$NC"
    echo ""
}

# Check arguments
if [ "$1" == "--help" ] || [ -z "$1" ] || [ -z "$2" ]; then
    show_usage
    exit 0
fi

REGISTRY_URL=$1
VERSION=$2
NO_CACHE=""
PUSH_ONLY=false

# Parse options
shift 2
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --push-only)
            PUSH_ONLY=true
            shift
            ;;
        *)
            print_color "Unknown option: $1" "$RED"
            show_usage
            exit 1
            ;;
    esac
done

print_color "============================================" "$BLUE"
print_color "  ThothAI - Build and Push Docker Images" "$BLUE"
print_color "============================================" "$BLUE"
echo ""
print_color "Registry: $REGISTRY_URL" "$YELLOW"
print_color "Version:  $VERSION" "$YELLOW"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_color "Error: Docker is not running" "$RED"
    exit 1
fi

# Array of images to build
declare -A IMAGES=(
    ["backend"]="docker/backend.Dockerfile:."
    ["frontend"]="docker/frontend.Dockerfile:./frontend"
    ["sql-generator"]="docker/sql-generator.Dockerfile:."
    ["proxy"]="docker/proxy.Dockerfile:./backend/proxy"
    ["mermaid-service"]="docker/mermaid-service/Dockerfile:./docker/mermaid-service"
)

# Build images
if [ "$PUSH_ONLY" = false ]; then
    print_color "=== PHASE 1: Build images ===" "$BLUE"
    echo ""
    
    for image_name in "${!IMAGES[@]}"; do
        IFS=':' read -r dockerfile context <<< "${IMAGES[$image_name]}"
        
        print_color "Building $image_name..." "$YELLOW"
        print_color "  Dockerfile: $dockerfile" "$NC"
        print_color "  Context: $context" "$NC"
        
        if docker build $NO_CACHE \
            -f "$dockerfile" \
            -t "thoth-$image_name:$VERSION" \
            -t "thoth-$image_name:latest" \
            -t "$REGISTRY_URL/thoth-$image_name:$VERSION" \
            -t "$REGISTRY_URL/thoth-$image_name:latest" \
            "$context"; then
            print_color "✓ Build completed for $image_name" "$GREEN"
        else
            print_color "✗ Error during build of $image_name" "$RED"
            exit 1
        fi
        echo ""
    done
    
    # Pull and tag Qdrant
    print_color "Pulling and tagging Qdrant..." "$YELLOW"
    if docker pull qdrant/qdrant:latest; then
        docker tag qdrant/qdrant:latest "$REGISTRY_URL/thoth-qdrant:$VERSION"
        docker tag qdrant/qdrant:latest "$REGISTRY_URL/thoth-qdrant:latest"
        print_color "✓ Qdrant ready" "$GREEN"
    else
        print_color "✗ Error during pull of Qdrant" "$RED"
        exit 1
    fi
    echo ""
else
    print_color "=== PHASE 1: Build skipped (--push-only) ===" "$YELLOW"
    echo ""
fi

# Push images
print_color "=== PHASE 2: Push images to registry ===" "$BLUE"
echo ""

# Check if logged in to registry
print_color "Checking registry login..." "$YELLOW"

# Determine if we are pushing to Docker Hub or a custom registry
# Docker Hub is implied if URL contains "docker.io" or has no dots/colons (e.g. just a username)
IS_DOCKER_HUB=false
if [[ "$REGISTRY_URL" == *"docker.io"* ]]; then
    IS_DOCKER_HUB=true
elif [[ "$REGISTRY_URL" != *"."* ]] && [[ "$REGISTRY_URL" != *":"* ]] && [[ "$REGISTRY_URL" != "localhost" ]]; then
    IS_DOCKER_HUB=true
fi

if [ "$IS_DOCKER_HUB" = true ]; then
    print_color "Docker Hub detected." "$NC"
    
    # Check if we have an active session for Docker Hub
    # "docker info" containing a Username indicates a valid login to the default registry
    if docker info 2>/dev/null | grep -q "Username"; then
        CURRENT_USER=$(docker info 2>/dev/null | grep "Username" | cut -d':' -f2 | xargs)
        print_color "✓ Already logged in as $CURRENT_USER" "$GREEN"
    else
        print_color "No active Docker Hub session found. Executing login:" "$YELLOW"
        if ! docker login; then
            print_color "✗ Login failed" "$RED"
            exit 1
        fi
    fi
else
    # For custom registries
    print_color "Custom registry detected: $REGISTRY_URL" "$NC"
    
    # Check if credentials exist in config.json to avoid unnecessary login prompts
    LOGGED_IN=false
    if [ -f "$HOME/.docker/config.json" ]; then
        if grep -q "$REGISTRY_URL" "$HOME/.docker/config.json"; then
            LOGGED_IN=true
        fi
    fi

    if [ "$LOGGED_IN" = true ]; then
        print_color "✓ Found credentials for $REGISTRY_URL in config" "$GREEN"
    else
        print_color "No credentials found for $REGISTRY_URL. Executing login:" "$YELLOW"
        if ! docker login "$REGISTRY_URL"; then
            print_color "✗ Login failed" "$RED"
            exit 1
        fi
    fi
fi
print_color "✓ Login verified" "$GREEN"
echo ""

# Push all images
ALL_IMAGES=("${!IMAGES[@]}" "qdrant")

for image_name in "${ALL_IMAGES[@]}"; do
    print_color "Pushing thoth-$image_name:$VERSION..." "$YELLOW"
    
    if docker push "$REGISTRY_URL/thoth-$image_name:$VERSION"; then
        print_color "✓ Push completed for thoth-$image_name:$VERSION" "$GREEN"
    else
        print_color "✗ Error during push of thoth-$image_name:$VERSION" "$RED"
        exit 1
    fi
    
    print_color "Pushing thoth-$image_name:latest..." "$YELLOW"
    if docker push "$REGISTRY_URL/thoth-$image_name:latest"; then
        print_color "✓ Push completed for thoth-$image_name:latest" "$GREEN"
    else
        print_color "✗ Error during push of thoth-$image_name:latest" "$RED"
        exit 1
    fi
    echo ""
done

print_color "============================================" "$GREEN"
print_color "  Build and Push completed successfully!" "$GREEN"
print_color "============================================" "$GREEN"
echo ""
print_color "Images available in registry:" "$YELLOW"
for image_name in "${ALL_IMAGES[@]}"; do
    print_color "  - $REGISTRY_URL/thoth-$image_name:$VERSION" "$NC"
done
echo ""
print_color "Next step:" "$BLUE"
print_color "  Configure secrets and deploy stack with:" "$NC"
print_color "  ./deploy-swarm.sh" "$GREEN"
echo ""
print_color "Note: Default ports for Swarm are 7000-7050" "$YELLOW"
print_color "  - Proxy (Web):     7010" "$NC"
print_color "  - Frontend:        7001" "$NC"
print_color "  - Backend:         7002 (via proxy)" "$NC"
print_color "  - SQL Generator:   7003" "$NC"
print_color "  - Mermaid Service: 7004" "$NC"
print_color "  - Qdrant:          7005" "$NC"
echo ""
