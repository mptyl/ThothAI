#!/usr/bin/env bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.
#
# Helper script to pull images from Docker Hub and install ThothAI locally.
# Does NOT build images associated with the project.

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
    print_header "ThothAI Docker Hub Installer"
    
    # 1. Check prerequisites
    if ! check_command docker; then exit 1; fi
    if ! check_command python3; then exit 1; fi

    # 2. Check config
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

    # 3. Generate configuration (.env.docker)
    print_color "Generating configuration..." "$YELLOW"
    python3 scripts/installer.py --generate-env-only
    print_color "✓ Configuration generated" "$GREEN"

    # 4. Extract Docker Username from config or use default
    DOCKER_USERNAME=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yml.local')).get('docker', {}).get('username', 'tylconsulting'))")
    export DOCKER_USERNAME
    print_color "Using Docker Registry User: $DOCKER_USERNAME" "$BLUE"

    # 5. Pull images
    print_header "Pulling Images from Docker Hub..."
    docker compose -f docker-compose-hub.yml pull

    # 6. Start services
    print_header "Starting Services..."
    # Ensure volumes/networks exist (installer.py usually does this, but we ran generate-env-only)
    # We need to create networks/volumes manually or trust compose to do it?
    # Compose creates volumes/networks referenced in the file if they are not 'external: true'.
    # In our compose file, many are 'external: true'. We need to create them.
    
    # Let's use a quick python snippet to call the creation methods or just do it via docker commands
    # Actually, scripts/installer.py has 'create_docker_volumes' and 'create_docker_network'.
    # We can't easily call just those methods via CLI flags.
    # Quick fix: We manually create them here.
    
    print_color "Ensuring network and volumes exist..." "$YELLOW"
    docker network create thoth-network 2>/dev/null || true
    
    VOLUMES="thoth-backend-static thoth-backend-media thoth-frontend-cache thoth-qdrant-data thoth-secrets thoth-shared-data"
    for vol in $VOLUMES; do
        docker volume create $vol 2>/dev/null || true
    done
    
    docker compose -f docker-compose-hub.yml up -d

    print_header "Installation Complete!"
    print_color "ThothAI is running." "$GREEN"
    print_color "Frontend: http://localhost:3040" "$GREEN"
    print_color "Backend:  http://localhost:8040/admin" "$GREEN"
}

main "$@"
