#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

echo "==================================="
echo "   ThothAI Unified Build Script    "
echo "==================================="

# Configuration
VERSION=${1:-latest}
REGISTRY=${DOCKER_REGISTRY:-marcopancotti}
PLATFORM=${2:-linux/amd64,linux/arm64}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    print_warning "Docker buildx not found. Installing..."
    docker buildx create --use --name thoth-builder
fi

print_status "Building ThothAI unified image v${VERSION}..."

# Build multi-platform image
docker buildx build \
    --platform ${PLATFORM} \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    -f docker/unified.Dockerfile \
    -t ${REGISTRY}/thoth:${VERSION} \
    -t ${REGISTRY}/thoth:latest \
    --cache-from type=registry,ref=${REGISTRY}/thoth:buildcache \
    --cache-to type=registry,ref=${REGISTRY}/thoth:buildcache,mode=max \
    --push \
    .

if [ $? -eq 0 ]; then
    print_status "Build successful!"
    print_status "Image published to ${REGISTRY}/thoth:${VERSION}"
    echo ""
    echo "To run the image:"
    echo "  docker run -d -p 80:80 -v \$(pwd)/exports:/app/exports --env-file .env ${REGISTRY}/thoth:${VERSION}"
else
    print_error "Build failed!"
    exit 1
fi