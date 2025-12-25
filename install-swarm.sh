#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# Script for deploying ThothAI to a remote Docker Swarm server

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

# Function to show usage
show_usage() {
    print_color "Usage: $0 --server <SSH_CONNECTION_STRING> [OPTIONS]" "$BLUE"
    print_color "" "$NC"
    print_color "Required Arguments:" "$YELLOW"
    print_color "  --server <SSH_CONNECTION_STRING>  SSH connection string (e.g., user@hostname or user@ip)" "$NC"
    print_color "" "$NC"
    print_color "Optional Arguments:" "$YELLOW"
    print_color "  --port <SSH_PORT>                 SSH port (default: 22)" "$NC"
    print_color "  --key <SSH_KEY_PATH>              Path to SSH private key (default: ~/.ssh/id_rsa)" "$NC"
    print_color "  --help                            Show this help message" "$NC"
    echo ""
    print_color "Example:" "$GREEN"
    print_color "  $0 --server user@192.168.1.100" "$NC"
    print_color "  $0 --server user@swarm.example.com --port 2222 --key ~/.ssh/custom_key" "$NC"
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

# Function to load swarm configuration
load_swarm_config() {
    local config_file="swarm_config.env"
    
    if [ ! -f "$config_file" ]; then
        print_color "Error: $config_file not found" "$RED"
        print_color "" "$NC"
        print_color "Please create $config_file by copying from the template:" "$YELLOW"
        print_color "  cp swarm_config.env.template $config_file" "$GREEN"
        print_color "" "$NC"
        print_color "Then edit $config_file with your configuration:" "$YELLOW"
        print_color "  - DOCKER_USERNAME (required for Docker Hub)" "$NC"
        print_color "  - STACK_NAME" "$NC"
        print_color "  - Service ports (if defaults conflict)" "$NC"
        exit 1
    fi
    
    # Source the configuration file
    set -a
    source "$config_file"
    set +a
    
    print_color "Configuration loaded from $config_file" "$GREEN"
}

# Function to validate configuration
validate_config() {
    if [ -z "$DOCKER_USERNAME" ]; then
        print_color "Error: DOCKER_USERNAME is not set in swarm_config.env" "$RED"
        print_color "Please set DOCKER_USERNAME to your Docker Hub username" "$YELLOW"
        exit 1
    fi
    
    if [ "$DOCKER_USERNAME" = "your-dockerhub-username" ]; then
        print_color "Error: DOCKER_USERNAME is still set to the default value" "$RED"
        print_color "Please edit swarm_config.env and set your actual Docker Hub username" "$YELLOW"
        exit 1
    fi
    
    # Set defaults for optional variables
    STACK_NAME=${STACK_NAME:-thoth}
    FRONTEND_PORT=${FRONTEND_PORT:-3040}
    BACKEND_PROXY_PORT=${BACKEND_PROXY_PORT:-8040}
    SQL_GENERATOR_PORT=${SQL_GENERATOR_PORT:-8020}
    QDRANT_PORT=${QDRANT_PORT:-6333}
    MERMAID_SERVICE_PORT=${MERMAID_SERVICE_PORT:-8003}
    WEB_PORT=${WEB_PORT:-7000}
    BACKEND_PORT=${BACKEND_PORT:-7002}
    
    print_color "Configuration validated:" "$GREEN"
    print_color "  DOCKER_USERNAME:         $DOCKER_USERNAME" "$NC"
    print_color "  STACK_NAME:              $STACK_NAME" "$NC"
    print_color "  FRONTEND_PORT:           $FRONTEND_PORT" "$NC"
    print_color "  BACKEND_PROXY_PORT:      $BACKEND_PROXY_PORT" "$NC"
    print_color "  SQL_GENERATOR_PORT:      $SQL_GENERATOR_PORT" "$NC"
    print_color "  QDRANT_PORT:             $QDRANT_PORT" "$NC"
    print_color "  MERMAID_SERVICE_PORT:    $MERMAID_SERVICE_PORT" "$NC"
    print_color "  WEB_PORT:                $WEB_PORT" "$NC"
    print_color "  BACKEND_PORT:            $BACKEND_PORT" "$NC"
}

# Function to build images locally
build_images() {
    print_color "=== Building Docker images locally ===" "$BLUE"
    echo ""
    
    if [ ! -f "install.sh" ]; then
        print_color "Error: install.sh not found in current directory" "$RED"
        exit 1
    fi
    
    print_color "Running ./install.sh to build images and generate .env.docker..." "$YELLOW"
    if bash ./install.sh; then
        print_color "✓ Images built successfully" "$GREEN"
    else
        print_color "✗ Failed to build images" "$RED"
        exit 1
    fi
}

# Function to tag images with Docker Hub username
tag_images() {
    print_color "=== Tagging images for Docker Hub ===" "$BLUE"
    echo ""
    
    local registry_url="$DOCKER_USERNAME"
    local version="latest"
    
    # Array of images to tag
    declare -A IMAGES=(
        ["backend"]="thoth-backend"
        ["frontend"]="thoth-frontend"
        ["sql-generator"]="thoth-sql-generator"
        ["proxy"]="thoth-proxy"
        ["mermaid-service"]="thoth-mermaid-service"
        ["qdrant"]="thoth-qdrant"
    )
    
    for local_name in "${!IMAGES[@]}"; do
        local image_name="${IMAGES[$local_name]}"
        
        if [ "$local_name" = "qdrant" ]; then
            # Qdrant is pulled from official registry
            print_color "Tagging qdrant/qdrant:latest..." "$YELLOW"
            if docker tag qdrant/qdrant:latest "$registry_url/$image_name:$version"; then
                print_color "✓ Tagged $registry_url/$image_name:$version" "$GREEN"
            else
                print_color "Warning: Could not tag qdrant/qdrant (may not exist locally)" "$YELLOW"
            fi
        else
            # Check if local image exists
            if docker images -q "thoth-$local_name:latest" > /dev/null 2>&1; then
                print_color "Tagging thoth-$local_name:latest..." "$YELLOW"
                if docker tag "thoth-$local_name:latest" "$registry_url/$image_name:$version"; then
                    print_color "✓ Tagged $registry_url/$image_name:$version" "$GREEN"
                else
                    print_color "✗ Failed to tag $image_name" "$RED"
                    exit 1
                fi
            else
                print_color "Warning: thoth-$local_name:latest not found, skipping" "$YELLOW"
            fi
        fi
    done
}

# Function to push images to Docker Hub
push_images() {
    print_color "=== Pushing images to Docker Hub ===" "$BLUE"
    echo ""
    
    local registry_url="$DOCKER_USERNAME"
    local version="latest"
    
    # Check if logged in to Docker Hub
    print_color "Checking Docker Hub login..." "$YELLOW"
    if ! docker info | grep -q "Username: $DOCKER_USERNAME"; then
        print_color "Please login to Docker Hub:" "$YELLOW"
        if ! docker login; then
            print_color "✗ Docker Hub login failed" "$RED"
            exit 1
        fi
    fi
    print_color "✓ Docker Hub login verified" "$GREEN"
    echo ""
    
    # Array of images to push
    declare -A IMAGES=(
        ["backend"]="thoth-backend"
        ["frontend"]="thoth-frontend"
        ["sql-generator"]="thoth-sql-generator"
        ["proxy"]="thoth-proxy"
        ["mermaid-service"]="thoth-mermaid-service"
        ["qdrant"]="thoth-qdrant"
    )
    
    for local_name in "${!IMAGES[@]}"; do
        local image_name="${IMAGES[$local_name]}"
        local full_tag="$registry_url/$image_name:$version"
        
        print_color "Pushing $full_tag..." "$YELLOW"
        if docker push "$full_tag"; then
            print_color "✓ Pushed $full_tag" "$GREEN"
        else
            print_color "✗ Failed to push $full_tag" "$RED"
            exit 1
        fi
    done
}

# Function to prepare docker-stack-swarm.yml
prepare_stack_file() {
    print_color "=== Preparing docker-stack-swarm.yml ===" "$BLUE"
    echo ""
    
    if [ ! -f "docker-stack.yml" ]; then
        print_color "Error: docker-stack.yml not found" "$RED"
        exit 1
    fi
    
    # Set environment variables for envsubst
    export REGISTRY_URL="$DOCKER_USERNAME"
    export VERSION="latest"
    export FRONTEND_PORT="$FRONTEND_PORT"
    export BACKEND_PORT="$BACKEND_PORT"
    export SQL_GENERATOR_PORT="$SQL_GENERATOR_PORT"
    export MERMAID_SERVICE_PORT="$MERMAID_SERVICE_PORT"
    export WEB_PORT="$WEB_PORT"
    
    # Create docker-stack-swarm.yml with substituted values
    print_color "Creating docker-stack-swarm.yml with port substitutions..." "$YELLOW"
    if envsubst < docker-stack.yml > docker-stack-swarm.yml; then
        print_color "✓ docker-stack-swarm.yml created" "$GREEN"
    else
        print_color "✗ Failed to create docker-stack-swarm.yml" "$RED"
        exit 1
    fi
}

# Function to deploy stack to remote Swarm
deploy_stack() {
    local ssh_server="$1"
    local ssh_port="$2"
    local ssh_key="$3"
    
    print_color "=== Deploying to remote Docker Swarm ===" "$BLUE"
    echo ""
    
    # Set DOCKER_HOST for SSH connection
    local docker_host="ssh://$ssh_server:$ssh_port"
    print_color "Setting DOCKER_HOST=$docker_host" "$YELLOW"
    export DOCKER_HOST="$docker_host"
    
    # Add SSH key to agent if specified
    if [ -n "$ssh_key" ] && [ -f "$ssh_key" ]; then
        print_color "Adding SSH key to agent..." "$YELLOW"
        ssh-add "$ssh_key" 2>/dev/null || print_color "Warning: Could not add SSH key to agent" "$YELLOW"
    fi
    
    # Check if Swarm is active on remote
    print_color "Checking Swarm status on remote host..." "$YELLOW"
    if ! docker info | grep -q "Swarm: active"; then
        print_color "Error: Docker Swarm is not active on the remote host" "$RED"
        print_color "Please initialize Swarm on the remote host: docker swarm init" "$YELLOW"
        exit 1
    fi
    print_color "✓ Swarm is active on remote host" "$GREEN"
    echo ""
    
    # Create secrets and configs on remote
    print_color "Creating secrets and configs on remote Swarm..." "$YELLOW"
    
    # Remove old secrets/configs if they exist
    docker secret rm "${STACK_NAME}_thoth_env_config" 2>/dev/null || true
    docker secret rm "${STACK_NAME}_thoth_config_yml" 2>/dev/null || true
    docker config rm "${STACK_NAME}_thoth_env_docker" 2>/dev/null || true
    
    # Create new secrets and configs
    if [ -f ".env.docker" ]; then
        if docker secret create "${STACK_NAME}_thoth_env_config" .env.docker; then
            print_color "✓ Created secret: ${STACK_NAME}_thoth_env_config" "$GREEN"
        else
            print_color "✗ Failed to create secret" "$RED"
            exit 1
        fi
    else
        print_color "Warning: .env.docker not found, skipping secret creation" "$YELLOW"
    fi
    
    if [ -f "config.yml.local" ]; then
        if docker secret create "${STACK_NAME}_thoth_config_yml" config.yml.local; then
            print_color "✓ Created secret: ${STACK_NAME}_thoth_config_yml" "$GREEN"
        else
            print_color "✗ Failed to create secret" "$RED"
            exit 1
        fi
    else
        print_color "Warning: config.yml.local not found, skipping secret creation" "$YELLOW"
    fi
    
    if [ -f ".env.docker" ]; then
        if docker config create "${STACK_NAME}_thoth_env_docker" .env.docker; then
            print_color "✓ Created config: ${STACK_NAME}_thoth_env_docker" "$GREEN"
        else
            print_color "✗ Failed to create config" "$RED"
            exit 1
        fi
    fi
    echo ""
    
    # Update docker-stack-swarm.yml with stack-specific secret/config names
    print_color "Updating docker-stack-swarm.yml with stack-specific names..." "$YELLOW"
    sed -i.tmp "s/thoth_env_config/${STACK_NAME}_thoth_env_config/g" docker-stack-swarm.yml
    sed -i.tmp "s/thoth_config_yml/${STACK_NAME}_thoth_config_yml/g" docker-stack-swarm.yml
    sed -i.tmp "s/thoth_env_docker/${STACK_NAME}_thoth_env_docker/g" docker-stack-swarm.yml
    rm -f docker-stack-swarm.yml.tmp
    print_color "✓ Updated docker-stack-swarm.yml" "$GREEN"
    echo ""
    
    # Deploy stack
    print_color "Deploying stack '$STACK_NAME' to remote Swarm..." "$YELLOW"
    if docker stack deploy -c docker-stack-swarm.yml "$STACK_NAME"; then
        print_color "✓ Stack deployment initiated" "$GREEN"
    else
        print_color "✗ Stack deployment failed" "$RED"
        exit 1
    fi
}

# Function to wait for services to start
wait_for_services() {
    print_color "=== Waiting for services to start ===" "$BLUE"
    echo ""
    
    local max_wait=600  # 10 minutes
    local elapsed=0
    
    while [ $elapsed -lt $max_wait ]; do
        local services=$(docker stack services "$STACK_NAME" --format "{{.Name}} {{.Replicas}}" 2>/dev/null || true)
        
        if [ -z "$services" ]; then
            print_color "Waiting for services to be created... ($elapsed/$max_wait seconds)" "$YELLOW"
            sleep 5
            elapsed=$((elapsed + 5))
            continue
        fi
        
        # Check if all services are running
        local all_running=true
        while IFS= read -r line; do
            local service_name=$(echo "$line" | awk '{print $1}')
            local replicas=$(echo "$line" | awk '{print $2}')
            
            if [[ ! "$replicas" =~ ^[0-9]+/[0-9]+$ ]] || [ "${replicas%/*}" -ne "${replicas#*/}" ]; then
                all_running=false
                break
            fi
        done <<< "$services"
        
        if [ "$all_running" = true ]; then
            print_color "✓ All services are running" "$GREEN"
            return 0
        fi
        
        print_color "Waiting for services... ($elapsed/$max_wait seconds)" "$YELLOW"
        print_color "$services" "$NC"
        sleep 10
        elapsed=$((elapsed + 10))
    done
    
    print_color "Timeout: Services did not start within $max_wait seconds" "$RED"
    return 1
}

# Function to show deployment status
show_deployment_status() {
    print_color "=== Deployment Status ===" "$BLUE"
    echo ""
    
    print_color "Stack services:" "$YELLOW"
    docker stack services "$STACK_NAME" 2>/dev/null || print_color "Could not retrieve services" "$RED"
    echo ""
    
    print_color "Stack tasks:" "$YELLOW"
    docker stack ps "$STACK_NAME" 2>/dev/null || print_color "Could not retrieve tasks" "$RED"
    echo ""
}

# Function to show access URLs
show_access_urls() {
    local ssh_server="$1"
    
    print_color "=== Access URLs ===" "$GREEN"
    echo ""
    
    print_color "The following services should be accessible at:" "$NC"
    print_color "  Frontend (Next.js):     http://$ssh_server:$FRONTEND_PORT" "$YELLOW"
    print_color "  Backend (Django):       http://$ssh_server:$BACKEND_PROXY_PORT/api" "$YELLOW"
    print_color "  Admin Panel:             http://$ssh_server:$BACKEND_PROXY_PORT/admin" "$YELLOW"
    print_color "  SQL Generator:          http://$ssh_server:$SQL_GENERATOR_PORT" "$YELLOW"
    print_color "  Mermaid Service:        http://$ssh_server:$MERMAID_SERVICE_PORT" "$YELLOW"
    print_color "  Qdrant Dashboard:       http://$ssh_server:$QDRANT_PORT/dashboard" "$YELLOW"
    print_color "  Web (Proxy):            http://$ssh_server:$WEB_PORT" "$YELLOW"
    echo ""
    
    print_color "Useful commands:" "$YELLOW"
    print_color "  View stack services:    docker stack services $STACK_NAME" "$NC"
    print_color "  View stack tasks:       docker stack ps $STACK_NAME" "$NC"
    print_color "  View service logs:      docker service logs ${STACK_NAME}_backend" "$NC"
    print_color "  Remove stack:           docker stack rm $STACK_NAME" "$NC"
    echo ""
}

# Main execution
main() {
    # Parse command line arguments
    SSH_SERVER=""
    SSH_PORT="22"
    SSH_KEY="$HOME/.ssh/id_rsa"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --server)
                SSH_SERVER="$2"
                shift 2
                ;;
            --port)
                SSH_PORT="$2"
                shift 2
                ;;
            --key)
                SSH_KEY="$2"
                shift 2
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
    
    # Validate required arguments
    if [ -z "$SSH_SERVER" ]; then
        print_color "Error: --server is required" "$RED"
        show_usage
        exit 1
    fi
    
    # Check SSH key exists
    if [ ! -f "$SSH_KEY" ]; then
        print_color "Warning: SSH key not found at $SSH_KEY" "$YELLOW"
        print_color "Continuing anyway (assuming SSH agent has the key or password auth)" "$YELLOW"
    fi
    
    print_color "============================================" "$BLUE"
    print_color "  ThothAI - Docker Swarm Deployment" "$BLUE"
    print_color "============================================" "$BLUE"
    echo ""
    
    print_color "Remote Server:" "$YELLOW"
    print_color "  Server:  $SSH_SERVER" "$NC"
    print_color "  Port:    $SSH_PORT" "$NC"
    print_color "  SSH Key: $SSH_KEY" "$NC"
    echo ""
    
    # Check prerequisites
    print_color "Checking prerequisites..." "$YELLOW"
    
    if ! check_command docker; then
        print_color "Error: Docker is not installed" "$RED"
        exit 1
    fi
    
    if ! check_command ssh; then
        print_color "Error: SSH client is not installed" "$RED"
        exit 1
    fi
    
    if ! check_command envsubst; then
        print_color "Error: envsubst is not available" "$RED"
        exit 1
    fi
    
    print_color "✓ Prerequisites OK" "$GREEN"
    echo ""
    
    # Load and validate configuration
    load_swarm_config
    validate_config
    echo ""
    
    # Build images locally
    build_images
    echo ""
    
    # Tag images
    tag_images
    echo ""
    
    # Push images
    push_images
    echo ""
    
    # Prepare stack file
    prepare_stack_file
    echo ""
    
    # Deploy to remote Swarm
    deploy_stack "$SSH_SERVER" "$SSH_PORT" "$SSH_KEY"
    echo ""
    
    # Wait for services
    if wait_for_services; then
        print_color "✓ Services started successfully" "$GREEN"
    else
        print_color "⚠ Some services may still be starting" "$YELLOW"
    fi
    echo ""
    
    # Show deployment status
    show_deployment_status
    echo ""
    
    # Show access URLs
    show_access_urls "$SSH_SERVER"
    
    print_color "============================================" "$GREEN"
    print_color "  Deployment completed!" "$GREEN"
    print_color "============================================" "$GREEN"
    echo ""
}

# Handle script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Run main function
main "$@"
