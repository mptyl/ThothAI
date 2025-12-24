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
            --local|--build)
                BUILD_LOCALLY=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--local|--build]"
                echo "  --local, --build: Build images locally instead of pulling from Docker Hub"
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

    # 6. Interactive choice if not specified via flag
    if [ "$BUILD_LOCALLY" = false ]; then
        print_color "Do you want to build images locally instead of pulling from Docker Hub?" "$BLUE"
        read -p "Enter 'build' for local build, or press Enter for Docker Hub [hub]: " choice
        if [ "$choice" == "build" ]; then
            BUILD_LOCALLY=true
        fi
    fi

    # 7. Prepare Images
    print_header "Preparing Images..."
    if [ "$BUILD_LOCALLY" = true ]; then
        print_color "Local build requested. Skipping Docker Hub pull." "$YELLOW"
        COMPOSE_FILE="docker-compose.yml"
        if docker compose -f docker-compose.yml build; then
            print_color "✓ Images built locally" "$GREEN"
        else
            print_color "Error: Local build failed. Please check your setup." "$RED"
            exit 1
        fi
    else
        # Default behavior: try to pull, fallback to build
        COMPOSE_FILE="docker-compose-hub.yml"
        print_color "Attempting to pull images from Docker Hub..." "$YELLOW"
        if docker compose -f docker-compose-hub.yml pull; then
            print_color "✓ Images pulled successfully from Docker Hub" "$GREEN"
        else
            print_color "WARNING: Docker Hub pull failed. Falling back to local build..." "$YELLOW"
            COMPOSE_FILE="docker-compose.yml"
            if docker compose -f docker-compose.yml build; then
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
    for vol in $VOLUMES; do
        docker volume create $vol 2>/dev/null || true
    done
    
    docker compose -f $COMPOSE_FILE up -d

    print_header "Installation Complete!"
    print_color "ThothAI is running using $COMPOSE_FILE." "$GREEN"
    print_color "Frontend: http://localhost:3040" "$GREEN"
    print_color "Backend:  http://localhost:8040/admin" "$GREEN"
}

main "$@"
