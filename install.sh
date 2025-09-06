#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

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

# Function to check command availability
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_color "Error: $1 is not installed" "$RED"
        return 1
    fi
    return 0
}

# Function to check Python version
check_python_version() {
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
        return 0
    else
        print_color "Error: Python 3.9+ is required" "$RED"
        return 1
    fi
}

# Function to show usage
show_usage() {
    print_color "Usage: $0 [OPTIONS]" "$BLUE"
    print_color "" "$NC"
    print_color "Options:" "$YELLOW"
    print_color "  --clean-cache    Clean Docker build cache before building" "$NC"
    print_color "  --prune-all      Prune all Docker resources (images, containers, volumes)" "$NC"
    print_color "  --help           Show this help message" "$NC"
    echo ""
}

# Main installation flow
main() {
    # Parse command line arguments
    CLEAN_CACHE=false
    PRUNE_ALL=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean-cache)
                CLEAN_CACHE=true
                shift
                ;;
            --prune-all)
                PRUNE_ALL=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_color "Unknown option: $1" "$RED"
                show_usage
                exit 1
                ;;
        esac
    done
    
    print_color "============================================" "$BLUE"
    print_color "       Thoth AI Installer" "$BLUE"
    print_color "============================================" "$BLUE"
    echo ""

    # Check for config.yml.local first
    if [ ! -f "config.yml.local" ]; then
        print_color "Error: Configuration file not found" "$RED"
        print_color "" "$NC"
        print_color "Please create config.yml.local with your installation parameters." "$YELLOW"
        print_color "You can copy config.yml as a template:" "$YELLOW"
        print_color "  cp config.yml config.yml.local" "$GREEN"
        print_color "" "$NC"
        print_color "Then edit config.yml.local with your:" "$YELLOW"
        print_color "  - AI provider API keys" "$NC"
        print_color "  - Embedding service configuration" "$NC"
        print_color "  - Database preferences" "$NC"
        print_color "  - Admin email (optional)" "$NC"
        print_color "  - Service ports (if defaults conflict)" "$NC"
        exit 1
    fi

    # Check prerequisites
    print_color "Checking prerequisites..." "$YELLOW"
    
    # Check for Docker
    if ! check_command docker; then
        print_color "Please install Docker first: https://www.docker.com" "$RED"
        exit 1
    fi
    
    # Check for Docker Compose
    if ! docker compose version &> /dev/null; then
        print_color "Error: Docker Compose is not available" "$RED"
        print_color "Please ensure Docker Desktop is installed with Compose support" "$RED"
        exit 1
    fi
    
    # Check for Python
    if ! check_command python3; then
        print_color "Please install Python 3.9+: https://www.python.org" "$RED"
        exit 1
    fi
    
    # Check Python version
    if ! check_python_version; then
        exit 1
    fi

    
    # Check for required Python packages
    print_color "Installing required Python packages..." "$YELLOW"
    
    # Check if we're in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        # In virtual environment, don't use --user
        pip3 install --quiet pyyaml requests toml 2>/dev/null || {
            print_color "Warning: Could not install Python packages. Trying with python -m pip..." "$YELLOW"
            python3 -m pip install --quiet pyyaml requests toml || {
                print_color "Error: Failed to install required Python packages" "$RED"
                print_color "Please run: pip3 install pyyaml requests toml" "$RED"
                exit 1
            }
        }
    else
        # Not in virtual environment, use --user
        pip3 install --quiet --user pyyaml requests toml 2>/dev/null || {
            print_color "Warning: Could not install Python packages. Trying with system pip..." "$YELLOW"
            python3 -m pip install --quiet --user pyyaml requests toml || {
                print_color "Error: Failed to install required Python packages" "$RED"
                print_color "Please run: pip3 install pyyaml requests toml" "$RED"
                exit 1
            }
        }
    fi
    
    print_color "Prerequisites OK" "$GREEN"
    echo ""
    
    # Clean Docker cache if requested
    if [ "$PRUNE_ALL" = true ]; then
        print_color "Pruning all Docker resources..." "$YELLOW"
        print_color "WARNING: This will remove all Docker images, containers, and volumes!" "$RED"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker system prune -a --volumes -f
            print_color "Docker resources pruned" "$GREEN"
        else
            print_color "Skipping Docker prune" "$YELLOW"
        fi
        echo ""
    elif [ "$CLEAN_CACHE" = true ]; then
        print_color "Cleaning Docker build cache..." "$YELLOW"
        docker builder prune -a -f
        print_color "Docker build cache cleaned" "$GREEN"
        echo ""
    fi

    # Validate configuration
    print_color "Validating configuration..." "$YELLOW"
    if python3 scripts/validate_config.py config.yml.local; then
        print_color "Configuration validation passed" "$GREEN"
    else
        print_color "Configuration validation failed" "$RED"
        print_color "Please fix the errors above and run again" "$RED"
        exit 1
    fi
    echo ""

    # Pass clean cache option to Python installer
    INSTALLER_ARGS=""
    if [ "$CLEAN_CACHE" = true ] || [ "$PRUNE_ALL" = true ]; then
        INSTALLER_ARGS="--no-cache"
    fi
    
    # Run installer
    print_color "Starting installation..." "$BLUE"
    if python3 scripts/installer.py $INSTALLER_ARGS; then
        print_color "" "$NC"
        print_color "============================================" "$GREEN"
        print_color "    Installation completed successfully!" "$GREEN"
        print_color "============================================" "$GREEN"
    else
        print_color "" "$NC"
        print_color "Installation failed" "$RED"
        print_color "Please check the error messages above" "$RED"
        exit 1
    fi
}

# Handle script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Run main function
main "$@"