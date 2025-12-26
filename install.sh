#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# Helper script to pull images from Docker Hub or build locally to install ThothAI.
# Use --build to force a local build.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_color() {
    echo -e "${2}${1}${NC}"
}

print_header() {
    echo ""
    print_color "============================================" "$BLUE"
    print_color "  $1" "$BLUE"
    print_color "============================================" "$BLUE"
    echo ""
}

# Check command availability
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_color "Error: $1 is not installed" "$RED"
        return 1
    fi
    return 0
}

main() {
    # 0. Parse arguments
    BUILD_LOCALLY=false
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build)
                BUILD_LOCALLY=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--build]"
                echo "  --build: Build images locally instead of pulling from Docker Hub"
                exit 0
                ;;
            *)
                shift
                ;;
        esac
    done

    # 1. Stop local development services to avoid port conflicts
    print_header "Cleaning up Local Services..."
    if [ -f "docker-compose-local.yml" ]; then
        docker compose -f docker-compose-local.yml down || true
        print_color "✓ Local development services stopped" "$GREEN"
    fi

    # 2. Check prerequisites
    if ! check_command docker; then exit 1; fi
    if ! check_command python3; then exit 1; fi

    # 3. Check config
    if [ ! -f "config.yml.local" ]; then
        if [ -f "config.yml" ]; then
             cp config.yml config.yml.local
             print_color "Created config.yml.local from template." "$YELLOW"
             print_color "Please edit config.yml.local and re-run this script." "$RED"
             exit 1
        else
            print_color "Error: config.yml.local and config.yml not found." "$RED"
            exit 1
        fi
    fi

    # 4. Generate configuration (.env.docker)
    print_color "Generating configuration..." "$YELLOW"
    python3 scripts/installer.py --generate-env-only
    print_color "✓ Configuration generated" "$GREEN"

    # 5. Extract Docker Username from config or use default
    DOCKER_USERNAME=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yml.local')).get('docker', {}).get('username', 'tylconsulting'))")
    export DOCKER_USERNAME
    print_color "Using Docker Registry User: $DOCKER_USERNAME" "$BLUE"

    # 6. Prepare Images
    print_header "Preparing Images..."
    if [ "$BUILD_LOCALLY" = true ]; then
        print_color "Local build requested. Skipping Docker Hub pull." "$YELLOW"
        COMPOSE_FILE="docker-compose.yml"
        if docker compose --env-file .env.docker -f docker-compose.yml build; then
            print_color "✓ Images built locally" "$GREEN"
        else
            print_color "Error: Local build failed. Please check your setup." "$RED"
            exit 1
        fi
    else
        # Default behavior: try to pull, fallback to build
        COMPOSE_FILE="docker-compose-hub.yml"
        print_color "Attempting to pull images from Docker Hub..." "$YELLOW"
        if docker compose --env-file .env.docker -f docker-compose-hub.yml pull; then
            print_color "✓ Images pulled successfully from Docker Hub" "$GREEN"
        else
            print_color "WARNING: Docker Hub pull failed. Falling back to local build..." "$YELLOW"
            COMPOSE_FILE="docker-compose.yml"
            if docker compose --env-file .env.docker -f docker-compose.yml build; then
                print_color "✓ Images built locally" "$GREEN"
            else
                print_color "Error: Local build failed. Please check your setup." "$RED"
                exit 1
            fi
        fi
    fi

    # 8. Start services
    print_header "Starting Services (using $COMPOSE_FILE)..."
    
    print_color "Ensuring network and volumes exist..." "$YELLOW"
    docker network create thoth-network 2>/dev/null || true
    
    VOLUMES="thoth-backend-static thoth-backend-media thoth-frontend-cache thoth-qdrant-data thoth-secrets thoth-shared-data"
    
    # Check if thoth-shared-data volume already exists and is initialized
    SHARED_DATA_EXISTS=false
    if docker volume inspect thoth-shared-data >/dev/null 2>&1; then
        # Volume exists, check if it has data (try to inspect a container using it)
        SHARED_DATA_EXISTS=true
    fi
    
    for vol in $VOLUMES; do
        docker volume create $vol 2>/dev/null || true
    done
    
    # Warning about slow data upload only for first run (when shared-data volume is new)
    if [ "$SHARED_DATA_EXISTS" = false ]; then
        print_color "⚠️  WARNING: Data loading in progress..." "$YELLOW"
        print_color "   Sample data will be loaded into the Docker volume." "$YELLOW"
        print_color "   This operation may take several minutes depending on disk speed." "$YELLOW"
        print_color "   The application will be available after this operation completes." "$YELLOW"
        echo ""
    fi
    
    docker compose --env-file .env.docker -f $COMPOSE_FILE up -d

    # Wait for backend to be healthy
    print_color "⏳ Waiting for backend to be ready..." "$YELLOW"
    if [ "$SHARED_DATA_EXISTS" = false ]; then
        print_color "   Data loading may take time (up to 20 minutes)..." "$YELLOW"
    fi
    echo ""

    MAX_RETRIES=120  # 20 minutes (120 * 10 seconds)
    RETRY_COUNT=0
    BACKEND_READY=false

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if docker exec thoth-backend curl -f http://localhost:8000/admin/login/ >/dev/null 2>&1; then
            BACKEND_READY=true
            print_color "✓ Backend ready!" "$GREEN"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        # Show progress every 10 retries (1 minute)
        if [ $((RETRY_COUNT % 10)) -eq 0 ]; then
            ELAPSED=$((RETRY_COUNT * 10 / 60))
            print_color "   Still waiting... (${ELAPSED} minutes elapsed)" "$YELLOW"
        else
            echo -n "."
        fi
        sleep 10
    done
    echo ""

    if [ "$BACKEND_READY" = false ]; then
        print_color "⚠️  Backend is not ready yet, but services are started." "$YELLOW"
        print_color "   Check logs with: docker logs -f thoth-backend" "$YELLOW"
        print_color "   The application may be available in a few minutes." "$YELLOW"
    fi

    print_header "Installation Complete!"
    print_color "ThothAI is running using $COMPOSE_FILE." "$GREEN"
    print_color "Frontend: http://localhost:3040" "$GREEN"
    print_color "Backend:  http://localhost:8040" "$GREEN"
}

main "$@"
