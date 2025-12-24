#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# ThothAI Docker Compose Installer
# This script installs ThothAI using Docker Compose for local deployment.
# For Docker Swarm deployment, use install-swarm.sh instead.

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

# Function to print section header
print_header() {
    echo ""
    print_color "============================================" "$BLUE"
    print_color "  $1" "$BLUE"
    print_color "============================================" "$BLUE"
    echo ""
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
    if $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
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
    print_color "ThothAI Docker Compose Installer" "$YELLOW"
    print_color "This script installs ThothAI using Docker Compose for local deployment." "$NC"
    print_color "" "$NC"
    print_color "Options:" "$YELLOW"
    print_color "  --clean-cache    Clean Docker build cache before building" "$NC"
    print_color "  --prune-all      Remove all ThothAI Docker resources (containers, images, volumes, networks)" "$NC"
    print_color "  --dry-run        Show what would be removed without actually removing anything" "$NC"
    print_color "  --force          Skip confirmation prompt (use with --prune-all)" "$NC"
    print_color "  --help           Show this help message" "$NC"
    echo ""
    print_color "Examples:" "$YELLOW"
    print_color "  $0                    # Standard installation" "$NC"
    print_color "  $0 --clean-cache      # Clean build cache before installing" "$NC"
    print_color "  $0 --prune-all        # Remove all ThothAI resources" "$NC"
    print_color "  $0 --prune-all --dry-run  # Preview what would be removed" "$NC"
    echo ""
    print_color "Note: For Docker Swarm deployment, use install-swarm.sh instead." "$YELLOW"
    echo ""
}

# Function to prune Docker resources
prune_resources() {
    local dry_run=$1
    local force=$2
    
    if [ "$dry_run" = true ]; then
        print_color "[DRY RUN] The following resources would be removed:" "$YELLOW"
        
        echo -e "\n[Containers]"
        docker ps -a --filter "name=^thoth-" --format "{{.Names}}" 2>/dev/null || true
        
        echo -e "\n[Volumes]"
        docker volume ls -q --filter "name=^thoth-" 2>/dev/null || true
        
        echo -e "\n[Networks]"
        docker network ls -q --filter "name=^thoth-" 2>/dev/null || true
        
        echo -e "\n[Images]"
        docker images --format "{{.Repository}}:{{.Tag}}" | grep -i "^thoth-" || true
        
        return 0
    fi
    
    if [ "$force" != true ]; then
        print_color "WARNING: This will remove all ThothAI containers, images, volumes, and networks!" "$RED"
        print_color "This includes all data stored in Docker volumes!" "$RED"
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_color "Operation cancelled" "$YELLOW"
            return 0
        fi
    fi
    
    print_color "Removing all ThothAI Docker resources..." "$YELLOW"
    
    # 1. Stop and remove all ThothAI containers
    print_color "Stopping and removing ThothAI containers..." "$YELLOW"
    docker ps -a -q --filter "name=^thoth-" --format "{{.ID}}" 2>/dev/null | xargs -r docker rm -f 2>/dev/null || true
    
    # 2. Remove all ThothAI volumes
    print_color "Removing ThothAI volumes..." "$YELLOW"
    docker volume ls -q --filter "name=^thoth-" 2>/dev/null | xargs -r docker volume rm 2>/dev/null || true
    
    # 3. Remove all ThothAI networks
    print_color "Removing ThothAI networks..." "$YELLOW"
    docker network ls -q --filter "name=^thoth-" 2>/dev/null | xargs -r docker network rm 2>/dev/null || true
    
    # 4. Remove all ThothAI images
    print_color "Removing ThothAI images..." "$YELLOW"
    docker images --format "{{.Repository}}:{{.Tag}}" | grep -i "^thoth-" | xargs -r docker rmi -f 2>/dev/null || true
    
    # 5. Remove any dangling ThothAI images
    print_color "Removing dangling ThothAI images..." "$YELLOW"
    docker images -f "dangling=true" --format "{{.ID}}" 2>/dev/null | while read -r image_id; do
        if docker history --no-trunc "$image_id" 2>/dev/null | grep -q "thoth"; then
            docker rmi -f "$image_id" 2>/dev/null || true
        fi
    done
    
    print_color "All ThothAI Docker resources have been removed" "$GREEN"
}

# Function to show deployment status
show_deployment_status() {
    print_header "Deployment Status"
    
    print_color "Docker Containers:" "$YELLOW"
    docker ps --filter "name=thoth-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || print_color "No containers running" "$YELLOW"
    echo ""
    
    print_color "Docker Volumes:" "$YELLOW"
    docker volume ls --filter "name=^thoth-" --format "table {{.Name}}\t{{.Driver}}" 2>/dev/null || print_color "No volumes found" "$YELLOW"
    echo ""
    
    print_color "Docker Networks:" "$YELLOW"
    docker network ls --filter "name=^thoth-" --format "table {{.Name}}\t{{.Driver}}" 2>/dev/null || print_color "No networks found" "$YELLOW"
    echo ""
}

# Main installation flow
main() {
    # Parse command line arguments
    CLEAN_CACHE=false
    PRUNE_ALL=false
    DRY_RUN=false
    FORCE=false
    
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
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
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
    
    print_header "ThothAI Docker Compose Installer"

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

    # Determine Python command (prefer python3, fallback to python)
    if check_command python3; then
        PYTHON_CMD=python3
    elif check_command python; then
        PYTHON_CMD=python
    else
        print_color "Please install Python 3.9+: https://www.python.org" "$RED"
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
    
    # Check Python version
    if ! check_python_version; then
        exit 1
    fi

    # Check for required Python packages
    print_color "Installing required Python packages..." "$YELLOW"
    
    # Check if uv is available (preferred)
    if check_command uv; then
        # Use uv pip install (works with uv-managed venvs)
        uv pip install --quiet pyyaml requests toml 2>/dev/null || {
            print_color "Error: Failed to install required Python packages with uv" "$RED"
            print_color "Please run: uv pip install pyyaml requests toml" "$RED"
            exit 1
        }
    elif [ -n "$VIRTUAL_ENV" ]; then
        # In virtual environment, don't use --user
        $PYTHON_CMD -m pip install --quiet pyyaml requests toml 2>/dev/null || {
            print_color "Warning: Could not install Python packages. Trying with python -m pip..." "$YELLOW"
            $PYTHON_CMD -m pip install --quiet pyyaml requests toml || {
                print_color "Error: Failed to install required Python packages" "$RED"
                print_color "Please run: pip install pyyaml requests toml" "$RED"
                exit 1
            }
        }
    else
        # Not in virtual environment, use --user
        $PYTHON_CMD -m pip install --quiet --user pyyaml requests toml 2>/dev/null || {
            print_color "Warning: Could not install Python packages. Trying with system pip..." "$YELLOW"
            $PYTHON_CMD -m pip install --quiet --user pyyaml requests toml || {
                print_color "Error: Failed to install required Python packages" "$RED"
                print_color "Please run: pip install --user pyyaml requests toml" "$RED"
                exit 1
            }
        }
    fi
    
    print_color "✓ Prerequisites OK" "$GREEN"
    echo ""
    
    # Clean Docker cache if requested
    if [ "$PRUNE_ALL" = true ]; then
        prune_resources "$DRY_RUN" "$FORCE"
        if [ "$DRY_RUN" = false ]; then
            echo ""
        fi
    elif [ "$CLEAN_CACHE" = true ]; then
        print_color "Cleaning Docker build cache..." "$YELLOW"
        docker builder prune -a -f
        print_color "✓ Docker build cache cleaned" "$GREEN"
        echo ""
    fi

    # Validate configuration
    print_color "Validating configuration..." "$YELLOW"
    if $PYTHON_CMD scripts/validate_config.py config.yml.local; then
        print_color "✓ Configuration validation passed" "$GREEN"
    else
        print_color "✗ Configuration validation failed" "$RED"
        print_color "Please fix the errors above and run again" "$RED"
        exit 1
    fi
    echo ""

    # Configure embedding provider dependencies
    print_color "Configuring embedding provider dependencies..." "$YELLOW"
    if ! $PYTHON_CMD scripts/configure_embedding.py config.yml.local; then
        print_color "" "$NC"
        print_color "============================================" "$RED"
        print_color "  CRITICAL: Failed to configure thoth-qdrant" "$RED"
        print_color "  The embedding service cannot be configured." "$RED"
        print_color "  Please check your configuration and try again." "$RED"
        print_color "============================================" "$RED"
        print_color "" "$NC"
        exit 1
    fi
    print_color "✓ Embedding configuration completed" "$GREEN"
    echo ""

    # Pass clean cache option to Python installer
    INSTALLER_ARGS=""
    if [ "$CLEAN_CACHE" = true ] || [ "$PRUNE_ALL" = true ]; then
        INSTALLER_ARGS="--no-cache"
    fi
    
    # Run installer
    print_header "Starting Docker Compose Installation"
    print_color "This will:" "$YELLOW"
    print_color "  1. Generate .env.docker from config.yml.local" "$NC"
    print_color "  2. Create Docker volumes and networks" "$NC"
    print_color "  3. Build Docker images locally" "$NC"
    print_color "  4. Start services with docker-compose up -d" "$NC"
    print_color "  5. Run initial setup commands" "$NC"
    echo ""
    print_color "This may take several minutes on first run..." "$YELLOW"
    echo ""
    
    if $PYTHON_CMD scripts/installer.py $INSTALLER_ARGS; then
        print_color "" "$NC"
        print_header "Installation completed successfully!"
        
        # Show deployment status
        show_deployment_status
        
        # Show access information
        print_header "Access Information"
        print_color "The following services are now available:" "$YELLOW"
        print_color "  Main Application:  http://localhost:8040" "$GREEN"
        print_color "  Frontend Direct:   http://localhost:3040" "$GREEN"
        print_color "  Backend API:       http://localhost:8040/api" "$GREEN"
        print_color "  Admin Panel:       http://localhost:8040/admin" "$GREEN"
        print_color "  SQL Generator:     http://localhost:8020" "$GREEN"
        print_color "  Qdrant Dashboard:  http://localhost:6333/dashboard" "$GREEN"
        print_color "  Mermaid Service:   http://localhost:8003" "$GREEN"
        echo ""
        
        print_color "Useful Commands:" "$YELLOW"
        print_color "  View logs:    docker compose logs -f" "$NC"
        print_color "  Stop:         docker compose down" "$NC"
        print_color "  Restart:      docker compose restart" "$NC"
        print_color "  Update:       git pull && ./install.sh" "$NC"
        echo ""
        
        print_color "For Docker Swarm deployment, use install-swarm.sh instead." "$YELLOW"
        echo ""
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
