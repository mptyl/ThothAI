#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Test Docker environment configuration

echo "Testing Docker Environment Configuration"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for .env.docker file
echo "1. Checking for .env.docker file..."
if [ -f ".env.docker" ]; then
    echo -e "${GREEN}✓ .env.docker found${NC}"
else
    echo -e "${RED}✗ .env.docker not found${NC}"
    exit 1
fi

# Check for renamed env files (should not exist)
echo ""
echo "2. Checking that old env files are renamed..."
OLD_ENV_FILES=(
    "backend/_env"
    "backend/.env"
    "frontend/.env.local"
    "frontend/.env.docker"
)

all_renamed=true
for file in "${OLD_ENV_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${RED}✗ Found unrenamed file: $file${NC}"
        all_renamed=false
    fi
done

if $all_renamed; then
    echo -e "${GREEN}✓ All old env files have been renamed${NC}"
fi

# Check Docker Compose configuration
echo ""
echo "3. Validating Docker Compose configuration..."
if docker-compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker Compose configuration is valid${NC}"
else
    echo -e "${RED}✗ Docker Compose configuration has errors${NC}"
    exit 1
fi

# Check that services reference .env.docker
echo ""
echo "4. Checking service configurations..."
services_with_env=$(docker-compose config | grep -c "env_file.*\.env\.docker" || true)
echo -e "${GREEN}✓ Found $services_with_env services using .env.docker${NC}"

# Check Docker network
echo ""
echo "5. Checking Docker network..."
if docker network ls | grep -q thoth-network; then
    echo -e "${GREEN}✓ thoth-network exists${NC}"
else
    echo -e "${YELLOW}! thoth-network not found. Run: docker network create thoth-network${NC}"
fi

# Test environment variable loading
echo ""
echo "6. Testing environment variable loading from .env.docker..."
source .env.docker 2>/dev/null
if [ ! -z "$FRONTEND_URL" ]; then
    echo -e "${GREEN}✓ FRONTEND_URL is set to: $FRONTEND_URL${NC}"
else
    echo -e "${RED}✗ FRONTEND_URL not found in .env.docker${NC}"
fi

if [ ! -z "$BACKEND_URL" ]; then
    echo -e "${GREEN}✓ BACKEND_URL is set to: $BACKEND_URL${NC}"
else
    echo -e "${RED}✗ BACKEND_URL not found in .env.docker${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}Docker environment check complete!${NC}"
echo ""
echo "To build and run Docker containers:"
echo "  docker-compose build"
echo "  docker-compose up -d"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"