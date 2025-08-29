#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Quiet Docker operations for Thoth

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Set quiet environment
export BUILDKIT_PROGRESS=plain
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

case "$1" in
    build)
        echo -e "${YELLOW}🔨 Building containers...${NC}"
        docker compose build --quiet 2>&1 | grep -v "^#" | grep -v "^Step" | grep -v "^ --->" | grep -v "^Removing" || true
        echo -e "${GREEN}[SUCCESS] Build complete${NC}"
        ;;
        
    up)
        echo -e "${YELLOW}[INFO] Starting services...${NC}"
        docker compose up -d
        echo -e "${GREEN}[SUCCESS] Services started${NC}"
        docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
        ;;
        
    rebuild)
        echo -e "${YELLOW}🔄 Rebuilding and starting...${NC}"
        docker compose build --quiet 2>&1 | grep -v "^#" | grep -v "^Step" | grep -v "^ --->" || true
        docker compose up -d
        echo -e "${GREEN}[SUCCESS] Complete${NC}"
        docker compose ps --format "table {{.Name}}\t{{.Status}}"
        ;;
        
    logs)
        # Show only last 50 lines and follow
        docker compose logs -f --tail=50 "$2"
        ;;
        
    status)
        docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
        ;;
        
    stop)
        echo -e "${YELLOW}⏹️  Stopping services...${NC}"
        docker compose stop
        echo -e "${GREEN}[SUCCESS] Stopped${NC}"
        ;;
        
    *)
        echo "Usage: $0 {build|up|rebuild|logs [service]|status|stop}"
        echo ""
        echo "Commands:"
        echo "  build   - Build containers quietly"
        echo "  up      - Start services with minimal output"
        echo "  rebuild - Build and start"
        echo "  logs    - Show recent logs (optional: specify service)"
        echo "  status  - Show container status"
        echo "  stop    - Stop all services"
        exit 1
        ;;
esac