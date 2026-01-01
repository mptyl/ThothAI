#!/usr/bin/env bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# Script for building and pushing multi-platform Docker images for Swarm/Kubernetes deployment

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
    print_color "  --platforms     Target platforms (default: linux/amd64,linux/arm64)" "$NC"
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
PLATFORMS="linux/amd64,linux/arm64"

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
        --platforms)
            PLATFORMS="$2"
            shift 2
            ;;
        *)
            print_color "Unknown option: $1" "$RED"
            show_usage
            exit 1
            ;;
    esac
done

print_color "=================================================" "$BLUE"
print_color "  ThothAI - Multi-platform Build and Push" "$BLUE"
print_color "=================================================" "$BLUE"
echo ""
print_color "Registry:  $REGISTRY_URL" "$YELLOW"
print_color "Version:   $VERSION" "$YELLOW"
print_color "Platforms: $PLATFORMS" "$YELLOW"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_color "Error: Docker is not running" "$RED"
    exit 1
fi

# Ensure buildx builder exists and is used
print_color "Checking buildx setup..." "$YELLOW"
if ! docker buildx ls | grep -q "thoth-builder"; then
    print_color "Creating new buildx builder 'thoth-builder'..." "$NC"
    docker buildx create --name thoth-builder --use --bootstrap
else
    docker buildx use thoth-builder
fi
print_color "✓ Buildx ready" "$GREEN"
echo ""

# Array of images to build
declare -A IMAGES=(
    ["backend"]="docker/backend.Dockerfile:."
    ["frontend"]="docker/frontend.Dockerfile:./frontend"
    ["sql-generator"]="docker/sql-generator.Dockerfile:."
    ["proxy"]="docker/proxy.Dockerfile:./backend/proxy"
    ["mermaid-service"]="docker/mermaid-service/Dockerfile:./docker/mermaid-service"
)

# Login Phase
print_color "=== PHASE 1: Registry Login ===" "$BLUE"
echo ""

# Determine if we are pushing to Docker Hub or a custom registry
IS_DOCKER_HUB=false
if [[ "$REGISTRY_URL" == *"docker.io"* ]]; then
    IS_DOCKER_HUB=true
elif [[ "$REGISTRY_URL" != *"."* ]] && [[ "$REGISTRY_URL" != *":"* ]] && [[ "$REGISTRY_URL" != "localhost" ]]; then
    IS_DOCKER_HUB=true
fi

if [ "$IS_DOCKER_HUB" = true ]; then
    print_color "Docker Hub detected." "$NC"
    if docker info 2>/dev/null | grep -q "Username"; then
        CURRENT_USER=$(docker info 2>/dev/null | grep "Username" | cut -d':' -f2 | xargs)
        print_color "✓ Already logged in as $CURRENT_USER" "$GREEN"
    else
        print_color "No active Docker Hub session found. Executing login:" "$YELLOW"
        if ! docker login; then exit 1; fi
    fi
else
    print_color "Custom registry detected: $REGISTRY_URL" "$NC"
    LOGGED_IN=false
    if [ -f "$HOME/.docker/config.json" ] && grep -q "$REGISTRY_URL" "$HOME/.docker/config.json"; then
        LOGGED_IN=true
    fi

    if [ "$LOGGED_IN" = true ]; then
        print_color "✓ Found credentials for $REGISTRY_URL" "$GREEN"
    else
        print_color "No credentials found. Executing login:" "$YELLOW"
        if ! docker login "$REGISTRY_URL"; then exit 1; fi
    fi
fi
print_color "✓ Login verified" "$GREEN"
echo ""

# Build & Push Phase
if [ "$PUSH_ONLY" = false ]; then
    print_color "=== PHASE 2: Build and Push (Multi-platform) ===" "$BLUE"
    echo ""
    
    for image_name in "${!IMAGES[@]}"; do
        IFS=':' read -r dockerfile context <<< "${IMAGES[$image_name]}"
        
        print_color "Building and Pushing $image_name..." "$YELLOW"
        print_color "  Platforms: $PLATFORMS" "$NC"
        
        if docker buildx build $NO_CACHE \
            --platform "$PLATFORMS" \
            -f "$dockerfile" \
            -t "$REGISTRY_URL/thoth-$image_name:$VERSION" \
            -t "$REGISTRY_URL/thoth-$image_name:latest" \
            --push \
            "$context"; then
            print_color "✓ Completed for $image_name" "$GREEN"
        else
            print_color "✗ Error during build/push of $image_name" "$RED"
            exit 1
        fi
        echo ""
    done
    
    # Qdrant handling via imagetools (preserves all original platforms)
    print_color "Processing Qdrant via imagetools..." "$YELLOW"
    if docker buildx imagetools create -t "$REGISTRY_URL/thoth-qdrant:$VERSION" qdrant/qdrant:latest && \
       docker buildx imagetools create -t "$REGISTRY_URL/thoth-qdrant:latest" qdrant/qdrant:latest; then
        print_color "✓ Qdrant ready (multi-platform preserved)" "$GREEN"
    else
        print_color "✗ Error during Qdrant processing" "$RED"
        exit 1
    fi
    echo ""
else
    print_color "=== PHASE 2: Build skipped (--push-only) ===" "$YELLOW"
    echo ""
    # In push-only mode with buildx, we would normally expect the manifest to already exist.
    # If the user really wants to push existing local images, they'd need a different flow,
    # but buildx multi-arch flows usually handle build-and-push together.
fi

print_color "=================================================" "$GREEN"
print_color "  Success! Multi-platform images pushed." "$GREEN"
print_color "=================================================" "$GREEN"
echo ""
print_color "Images available in registry for $PLATFORMS:" "$YELLOW"
for image_name in "${!IMAGES[@]}"; do
    print_color "  - $REGISTRY_URL/thoth-$image_name:$VERSION" "$NC"
done
print_color "  - $REGISTRY_URL/thoth-qdrant:$VERSION" "$NC"
echo ""
print_color "Next step: ./deploy-swarm.sh" "$BLUE"
echo ""

