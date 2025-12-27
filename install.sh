#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# Helper script to install ThothAI by pulling from Docker Hub or building locally.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

show_usage() {
    print_color "Usage: $0 [OPTIONS]" "$BLUE"
    echo ""
    print_color "ThothAI Docker Compose Installer" "$YELLOW"
    echo "This script installs ThothAI using Docker Compose for local deployment."
    echo ""
    print_color "Options:" "$YELLOW"
    echo "  --build         Build images locally instead of pulling from Docker Hub"
    echo "  --pull          Pull images from Docker Hub (default)"
    echo "  --clean-cache   Clean Docker build cache before building"
    echo "  --prune         Remove all ThothAI Docker resources (containers, images, volumes, networks)"
    echo "  --force         Skip confirmation prompt (use with --prune)"
    echo "  --help, -h      Show this help message"
    echo ""
    print_color "Examples:" "$YELLOW"
    echo "  $0                # Standard installation (pull from Hub)"
    echo "  $0 --build        # Build images locally"
    echo "  $0 --prune        # Remove all ThothAI resources"
    echo ""
}

# Check command availability
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_color "Error: $1 is not installed" "$RED"
        return 1
    fi
    return 0
}

main() {
    # 1. Parse arguments
    INSTALLER_ARGS=()
    PRUNE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build)       INSTALLER_ARGS+=("--build"); shift ;;
            --pull)        INSTALLER_ARGS+=("--pull"); shift ;;
            --prune)       INSTALLER_ARGS+=("--prune"); PRUNE=true; shift ;;
            --clean-cache) INSTALLER_ARGS+=("--clean-cache"); shift ;;
            --force)       INSTALLER_ARGS+=("--force"); shift ;;
            --help|-h)     show_usage; exit 0 ;;
            *)             shift ;;
        esac
    done

    print_header "ThothAI Docker Compose Installer"

    # 2. Check prerequisites
    if ! check_command docker; then exit 1; fi
    if ! check_command python3; then exit 1; fi
    
    # Check for required Python packages
    print_color "Checking Python dependencies..." "$YELLOW"
    python3 -m pip install --quiet pyyaml requests toml --user 2>/dev/null || \
    python3 -m pip install --quiet pyyaml requests toml || \
    print_color "Warning: Could not install dependencies automatically. Please run: pip install pyyaml requests toml" "$YELLOW"

    # 3. Clean up Local development services to avoid port conflicts (if not pruning)
    if [ "$PRUNE" = false ]; then
        if [ -f "docker-compose-local.yml" ]; then
            print_color "Stopping local development services to avoid port conflicts..." "$YELLOW"
            docker compose -f docker-compose-local.yml down 2>/dev/null || true
        fi
    fi

    # 4. Check for config.yml.local first
    if [ ! -f "config.yml.local" ]; then
        if [ -f "config.yml" ]; then
             cp config.yml config.yml.local
             print_color "Created config.yml.local from template." "$YELLOW"
             print_color "Please edit config.yml.local with your AI API keys and re-run this script." "$RED"
             exit 1
        else
            print_color "Error: config.yml.local and config.yml not found." "$RED"
            exit 1
        fi
    fi

    # 5. Run Validation and Configuration scripts (if not pruning)
    if [ "$PRUNE" = false ]; then
        print_color "Validating configuration..." "$YELLOW"
        python3 scripts/validate_config.py config.yml.local || exit 1
        
        print_color "Configuring embedding provider dependencies..." "$YELLOW"
        python3 scripts/configure_embedding.py config.yml.local || exit 1
    fi

    # 6. Execute Installer
    python3 scripts/installer.py "${INSTALLER_ARGS[@]}"
}

main "$@"
