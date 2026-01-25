#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# Script for deploying ThothAI to Docker Swarm (Local or Remote)

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
    print_color "ThothAI Docker Swarm Installer" "$YELLOW"
    echo "Deploys ThothAI to a Docker Swarm cluster (local or remote)."
    echo ""
    print_color "Options:" "$YELLOW"
    echo "  --server <SSH_STING>  Deploy to remote server via SSH (e.g., user@hostname)"
    echo "  --port <SSH_PORT>     SSH port for remote deploy (default: 22)"
    echo "  --key <SSH_KEY_PATH>  Path to SSH private key (default: ~/.ssh/id_rsa)"
    echo "  --skip-pull           Skip pulling images from Docker Hub"
    echo "  --skip-secrets        Skip creating/recreating secrets and configs"
    echo "  --prune               Remove the stack and associated secrets/configs"
    echo "  --help, -h            Show this help message"
    echo ""
    print_color "Examples:" "$YELLOW"
    echo "  $0                  # Local Swarm deployment"
    echo "  $0 --server user@ip # Remote Swarm deployment"
    echo "  $0 --prune          # Remove local stack"
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

# Load swarm configuration
load_swarm_config() {
    local config_file="swarm_config.env"
    if [ ! -f "$config_file" ]; then
        if [ -f "swarm_config.env.template" ]; then
            cp swarm_config.env.template "$config_file"
            print_color "Created $config_file from template. Please edit it and re-run." "$YELLOW"
            exit 1
        else
            print_color "Error: $config_file not found." "$RED"
            exit 1
        fi
    fi
    set -a; source "$config_file"; set +a
    print_color "✓ Configuration loaded from $config_file" "$GREEN"
}

# Validate configuration
validate_config() {
    DOCKER_USERNAME=${DOCKER_USERNAME:-tylconsulting}
    if [ "$DOCKER_USERNAME" = "your-dockerhub-username" ]; then
        print_color "Error: Please set DOCKER_USERNAME in swarm_config.env" "$RED"
        exit 1
    fi
    STACK_NAME=${STACK_NAME:-thothai-swarm}
    VERSION=${VERSION:-latest}
    
    # Defaults and alignment
    FRONTEND_PORT=${FRONTEND_PORT:-7001}
    BACKEND_PORT=${BACKEND_PORT:-7002}
    SQL_GENERATOR_PORT=${SQL_GENERATOR_PORT:-7003}
    MERMAID_SERVICE_PORT=${MERMAID_SERVICE_PORT:-7004}
    QDRANT_PORT=${QDRANT_PORT:-7005}
    WEB_PORT=${WEB_PORT:-7000}
    BACKEND_PROXY_PORT=${BACKEND_PROXY_PORT:-$WEB_PORT}
    
    # Export for envsubst
    export DOCKER_USERNAME STACK_NAME VERSION
    export FRONTEND_PORT BACKEND_PORT SQL_GENERATOR_PORT MERMAID_SERVICE_PORT QDRANT_PORT WEB_PORT BACKEND_PROXY_PORT
}

# Pull images
pull_images() {
    print_header "Pulling Images..."
    local images=("thoth-backend" "thoth-frontend" "thoth-sql-generator" "thoth-proxy" "thoth-mermaid-service")
    for img in "${images[@]}"; do
        print_color "Pulling $DOCKER_USERNAME/$img:$VERSION..." "$YELLOW"
        docker pull "$DOCKER_USERNAME/$img:$VERSION"
    done
    docker pull qdrant/qdrant:latest
    print_color "✓ All images pulled" "$GREEN"
}

# Prepare stack file
prepare_stack_file() {
    print_color "Preparing deployment file..." "$YELLOW"
    # Export vars for envsubst
    export REGISTRY_URL="$DOCKER_USERNAME"
    export DOCKER_REGISTRY="$DOCKER_USERNAME"
    export APP_HOST="${STACK_NAME}_backend"
    export FRONTEND_HOST="${STACK_NAME}_frontend"
    export SQL_GEN_HOST="${STACK_NAME}_sql-generator"
    
    if ! envsubst < docker-stack.yml > docker-stack-swarm.yml; then
        print_color "Error: envsubst failed" "$RED"
        exit 1
    fi
    
    # Substitute stack-specific secret/config names
    sed -i.tmp "s/thoth_env_config/${STACK_NAME}_thoth_env_config/g" docker-stack-swarm.yml
    sed -i.tmp "s/thoth_config_yml/${STACK_NAME}_thoth_config_yml/g" docker-stack-swarm.yml
    sed -i.tmp "s/thoth_env_docker/${STACK_NAME}_thoth_env_docker/g" docker-stack-swarm.yml
    rm -f docker-stack-swarm.yml.tmp
    print_color "✓ docker-stack-swarm.yml ready" "$GREEN"
}

# Create secrets and configs
manage_secrets() {
    print_header "Managing Secrets and Configs..."
    
    # Generate .env.docker if script exists
    if [ -f "scripts/installer.py" ]; then
        python3 scripts/installer.py --generate-env-only
    fi

    # Remove existing
    docker secret rm "${STACK_NAME}_thoth_env_config" "${STACK_NAME}_thoth_config_yml" 2>/dev/null || true
    docker config rm "${STACK_NAME}_thoth_env_docker" 2>/dev/null || true
    
    # Create new
    [ -f ".env.docker" ] && docker secret create "${STACK_NAME}_thoth_env_config" .env.docker
    [ -f "config.yml.local" ] && docker secret create "${STACK_NAME}_thoth_config_yml" config.yml.local
    [ -f ".env.docker" ] && docker config create "${STACK_NAME}_thoth_env_docker" .env.docker
    print_color "✓ Secrets and configs created" "$GREEN"
}

# Prune resources
prune_swarm() {
    print_header "Pruning Swarm Stack: $STACK_NAME"
    docker stack rm "$STACK_NAME" 2>/dev/null || true
    print_color "Stack removal initiated. Cleaning up secrets..." "$YELLOW"
    sleep 5
    docker secret rm "${STACK_NAME}_thoth_env_config" "${STACK_NAME}_thoth_config_yml" 2>/dev/null || true
    docker config rm "${STACK_NAME}_thoth_env_docker" 2>/dev/null || true
    print_color "✓ Prune completed" "$GREEN"
}

# Wait for services
wait_for_services() {
    print_header "Waiting for services to start..."
    local max_wait=300
    local elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        local replicas=$(docker stack services "$STACK_NAME" --format "{{.Replicas}}" | grep -v "0/0" || true)
        if [ -n "$replicas" ]; then
            local all_ready=true
            while read -r r; do
                if [[ "${r%/*}" -ne "${r#*/}" ]]; then all_ready=false; fi
            done <<< "$replicas"
            if [ "$all_ready" = true ]; then
                print_color "✓ All services are running" "$GREEN"
                return 0
            fi
        fi
        echo -n "."
        sleep 5
        elapsed=$((elapsed + 5))
    done
    print_color "Timeout waiting for services" "$YELLOW"
}

main() {
    SSH_SERVER=""
    SSH_PORT="22"
    SSH_KEY="$HOME/.ssh/id_rsa"
    SKIP_PULL=false
    SKIP_SECRETS=false
    PRUNE=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --server)       SSH_SERVER="$2"; shift 2 ;;
            --port)         SSH_PORT="$2"; shift 2 ;;
            --key)          SSH_KEY="$2"; shift 2 ;;
            --skip-pull)    SKIP_PULL=true; shift ;;
            --skip-secrets) SKIP_SECRETS=true; shift ;;
            --prune)        PRUNE=true; shift ;;
            --help|-h)      show_usage; exit 0 ;;
            *)              shift ;;
        esac
    done

    print_header "ThothAI Swarm Deployment"
    
    # 1. Prerequisites
    check_command docker; check_command envsubst
    
    # 2. Remote setup
    if [ -n "$SSH_SERVER" ]; then
        print_color "Target: Remote Swarm ($SSH_SERVER)" "$BLUE"
        export DOCKER_HOST="ssh://$SSH_SERVER:$SSH_PORT"
        if [ -f "$SSH_KEY" ]; then export DOCKER_SSH_CLIENT_KEY="$SSH_KEY"; fi
    else
        print_color "Target: Local Swarm" "$BLUE"
    fi

    # 3. Load config
    load_swarm_config
    validate_config

    # 4. Prune if requested
    if [ "$PRUNE" = true ]; then
        prune_swarm
        exit 0
    fi

    # 5. Execute deployment
    [ "$SKIP_PULL" = false ] && pull_images
    [ "$SKIP_SECRETS" = false ] && manage_secrets
    
    # Ensure required volumes exist
    print_color "Ensuring required volumes exist..." "$YELLOW"
    local volumes=("thoth-secrets" "thoth-backend-static" "thoth-backend-media" "thoth-frontend-cache" "thoth-qdrant-data" "thoth-shared-data" "thoth-data-exchange")
    for vol in "${volumes[@]}"; do
        if ! docker volume ls --format '{{.Name}}' | grep -q "^${vol}$"; then
            docker volume create "$vol" >/dev/null 2>&1
            print_color "  Created volume '$vol'" "$GREEN"
        fi
    done
    
    # Ensure network exists
    docker network create --driver overlay --attachable "${STACK_NAME}_thoth-network" 2>/dev/null || true
    
    prepare_stack_file
    
    print_color "Deploying stack $STACK_NAME..." "$YELLOW"
    docker stack deploy -c docker-stack-swarm.yml "$STACK_NAME"
    
    wait_for_services

    # 6. Show URLs
    HOST="localhost"
    if [ -n "$SSH_SERVER" ]; then HOST=$(echo "$SSH_SERVER" | cut -d'@' -f2); fi
    
    print_header "Deployment Complete!"
    print_color "Main Access: http://$HOST:$WEB_PORT" "$GREEN"
    print_color "Frontend Service: http://$HOST:$FRONTEND_PORT" "$GREEN"
    print_color "Backend Admin: http://$HOST:$BACKEND_PROXY_PORT/admin" "$GREEN"
    
    rm -f docker-stack-swarm.yml
}

main "$@"
