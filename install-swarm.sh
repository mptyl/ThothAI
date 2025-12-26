#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# Script for deploying ThothAI to a remote Docker Swarm server using images from Docker Hub

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
    print_color "Usage: $0 [OPTIONS]" "$BLUE"
    print_color "" "$NC"
    print_color "Options:" "$YELLOW"
    print_color "  --server <SSH_CONNECTION_STRING>  Deploy to remote server via SSH (REQUIRED)" "$NC"
    print_color "  --port <SSH_PORT>                 SSH port (default: 22)" "$NC"
    print_color "  --key <SSH_KEY_PATH>              Path to SSH private key (default: ~/.ssh/id_rsa)" "$NC"
    print_color "  --skip-pull                       Skip pulling images from Docker Hub" "$NC"
    print_color "  --skip-secrets                    Skip creating secrets and configs" "$NC"
    print_color "  --help                            Show this help message" "$NC"
    echo ""
    print_color "Description:" "$GREEN"
    print_color "  Deploys ThothAI to a remote Docker Swarm server using pre-built images from Docker Hub." "$NC"
    print_color "  No local build is required - images are pulled directly from Docker Hub." "$NC"
    print_color "  Manages SSH connection to the remote server for deployment." "$NC"
    print_color "" "$NC"
    print_color "Examples:" "$GREEN"
    print_color "  $0 --server user@192.168.1.100" "$NC"
    print_color "  $0 --server user@swarm.example.com --port 2222 --key ~/.ssh/custom_key" "$NC"
    print_color "  $0 --server admin@10.0.0.50 --skip-pull" "$NC"
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

# Function to prompt for server if not provided
prompt_for_server() {
    print_color "No server specified. Please enter the SSH connection string:" "$YELLOW"
    print_color "Format: user@hostname or user@ip_address" "$NC"
    read -p "SSH connection string: " SSH_SERVER_INPUT
    
    if [ -z "$SSH_SERVER_INPUT" ]; then
        print_color "Error: SSH connection string is required" "$RED"
        exit 1
    fi
    
    echo "$SSH_SERVER_INPUT"
}

# Function to test SSH connection
test_ssh_connection() {
    local ssh_server="$1"
    local ssh_port="$2"
    local ssh_key="$3"
    
    print_color "Testing SSH connection to $ssh_server:$ssh_port..." "$YELLOW"
    
    local ssh_cmd="ssh"
    if [ -n "$ssh_key" ] && [ -f "$ssh_key" ]; then
        ssh_cmd="ssh -i $ssh_key -p $ssh_port -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"
    else
        ssh_cmd="ssh -p $ssh_port -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"
    fi
    
    if $ssh_cmd "$ssh_server" "echo 'Connection successful'" > /dev/null 2>&1; then
        print_color "✓ SSH connection successful" "$GREEN"
        return 0
    else
        print_color "✗ SSH connection failed" "$RED"
        print_color "Please check:" "$YELLOW"
        print_color "  - Server address and user are correct" "$NC"
        print_color "  - SSH key path is correct (if using key auth)" "$NC"
        print_color "  - SSH key is loaded in ssh-agent or password is correct" "$NC"
        print_color "  - Server is reachable and SSH service is running" "$NC"
        return 1
    fi
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
    STACK_NAME=${STACK_NAME:-thothai-swarm}
    FRONTEND_PORT=${FRONTEND_PORT:-7001}
    BACKEND_PROXY_PORT=${BACKEND_PROXY_PORT:-7000}
    SQL_GENERATOR_PORT=${SQL_GENERATOR_PORT:-7003}
    QDRANT_PORT=${QDRANT_PORT:-7005}
    MERMAID_SERVICE_PORT=${MERMAID_SERVICE_PORT:-7004}
    WEB_PORT=${WEB_PORT:-7000}
    BACKEND_PORT=${BACKEND_PORT:-7002}
    VERSION=${VERSION:-latest}
    
    print_color "Configuration validated:" "$GREEN"
    print_color "  DOCKER_USERNAME:         $DOCKER_USERNAME" "$NC"
    print_color "  STACK_NAME:              $STACK_NAME" "$NC"
    print_color "  VERSION:                 $VERSION" "$NC"
    print_color "  FRONTEND_PORT:           $FRONTEND_PORT" "$NC"
    print_color "  BACKEND_PROXY_PORT:      $BACKEND_PROXY_PORT" "$NC"
    print_color "  SQL_GENERATOR_PORT:      $SQL_GENERATOR_PORT" "$NC"
    print_color "  QDRANT_PORT:             $QDRANT_PORT" "$NC"
    print_color "  MERMAID_SERVICE_PORT:    $MERMAID_SERVICE_PORT" "$NC"
    print_color "  WEB_PORT:                $WEB_PORT" "$NC"
    print_color "  BACKEND_PORT:            $BACKEND_PORT" "$NC"
}

# Function to pull images from Docker Hub
pull_images() {
    print_color "=== Pulling images from Docker Hub ===" "$BLUE"
    echo ""
    
    local registry_url="$DOCKER_USERNAME"
    
    # Array of images to pull
    declare -A IMAGES=(
        ["backend"]="thoth-backend"
        ["frontend"]="thoth-frontend"
        ["sql-generator"]="thoth-sql-generator"
        ["proxy"]="thoth-proxy"
        ["mermaid-service"]="thoth-mermaid-service"
    )
    
    for local_name in "${!IMAGES[@]}"; do
        local image_name="${IMAGES[$local_name]}"
        local full_tag="$registry_url/$image_name:$VERSION"
        
        print_color "Pulling $full_tag..." "$YELLOW"
        if docker pull "$full_tag"; then
            print_color "✓ Pulled $full_tag" "$GREEN"
        else
            print_color "✗ Failed to pull $full_tag" "$RED"
            print_color "Note: Make sure images exist on Docker Hub at $registry_url/$image_name:$VERSION" "$YELLOW"
            exit 1
        fi
    done
    
    # Pull Qdrant from official registry
    print_color "Pulling qdrant/qdrant:latest..." "$YELLOW"
    if docker pull qdrant/qdrant:latest; then
        print_color "✓ Pulled qdrant/qdrant:latest" "$GREEN"
    else
        print_color "✗ Failed to pull qdrant/qdrant:latest" "$RED"
        exit 1
    fi
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
    export VERSION="$VERSION"
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
deploy_stack_remote() {
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
    
    # Create network if it doesn't exist
    print_color "Ensuring network exists..." "$YELLOW"
    if ! docker network ls | grep -q "${STACK_NAME}_thoth-network"; then
        print_color "Creating network ${STACK_NAME}_thoth-network..." "$YELLOW"
        docker network create --driver overlay --attachable "${STACK_NAME}_thoth-network"
        print_color "✓ Network created" "$GREEN"
    else
        print_color "✓ Network already exists" "$GREEN"
    fi
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

# Function to show access URLs for remote deployment
show_access_urls_remote() {
    local ssh_server="$1"
    
    # Extract IP/hostname from SSH connection string
    local server_address=$(echo "$ssh_server" | cut -d'@' -f2)
    
    print_color "=== Access URLs ===" "$GREEN"
    echo ""
    
    print_color "The following services should be accessible at:" "$NC"
    print_color "  Frontend (Next.js):     http://$server_address:$FRONTEND_PORT" "$YELLOW"
    print_color "  Backend (Django):       http://$server_address:$BACKEND_PROXY_PORT/api" "$YELLOW"
    print_color "  Admin Panel:             http://$server_address:$BACKEND_PROXY_PORT/admin" "$YELLOW"
    print_color "  SQL Generator:          http://$server_address:$SQL_GENERATOR_PORT" "$YELLOW"
    print_color "  Mermaid Service:        http://$server_address:$MERMAID_SERVICE_PORT" "$YELLOW"
    print_color "  Qdrant Dashboard:       http://$server_address:$QDRANT_PORT/dashboard" "$YELLOW"
    print_color "  Web (Proxy):            http://$server_address:$WEB_PORT" "$YELLOW"
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
    SKIP_PULL=false
    SKIP_SECRETS=false
    
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
            --skip-pull)
                SKIP_PULL=true
                shift
                ;;
            --skip-secrets)
                SKIP_SECRETS=true
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
    
    # Prompt for server if not provided
    if [ -z "$SSH_SERVER" ]; then
        SSH_SERVER=$(prompt_for_server)
    fi
    
    print_color "============================================" "$BLUE"
    print_color "  ThothAI - Remote Docker Swarm Deployment" "$BLUE"
    print_color "  Using images from Docker Hub" "$BLUE"
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
    
    # Test SSH connection
    if ! test_ssh_connection "$SSH_SERVER" "$SSH_PORT" "$SSH_KEY"; then
        exit 1
    fi
    echo ""
    
    # Load and validate configuration
    load_swarm_config
    validate_config
    echo ""
    
    # Pull images from Docker Hub
    if [ "$SKIP_PULL" = false ]; then
        pull_images
        echo ""
    else
        print_color "Skipping image pull (using cached images)" "$YELLOW"
        echo ""
    fi
    
    # Prepare stack file
    prepare_stack_file
    
    # Deploy to remote Swarm
    deploy_stack_remote "$SSH_SERVER" "$SSH_PORT" "$SSH_KEY"
    echo ""
    
    # Wait for services
    if wait_for_services; then
        print_color "✓ Services started successfully" "$GREEN"
        echo ""
        
        # Show deployment status
        show_deployment_status
        echo ""
        
        # Show access URLs
        show_access_urls_remote "$SSH_SERVER"
        
        print_color "============================================" "$GREEN"
        print_color "  Remote deployment completed!" "$GREEN"
        print_color "============================================" "$GREEN"
        echo ""
    else
        print_color "✗ Services failed to start within timeout" "$RED"
        echo ""
        
        print_color "=== Deployment Status ===" "$YELLOW"
        show_deployment_status
        echo ""
        
        print_color "To debug, check service logs:" "$YELLOW"
        print_color "  docker service logs ${STACK_NAME}_backend" "$NC"
        print_color "  docker service logs ${STACK_NAME}_proxy" "$NC"
        print_color "  docker service logs ${STACK_NAME}_frontend" "$NC"
        echo ""
        
        print_color "To remove the failed stack:" "$YELLOW"
        print_color "  docker stack rm ${STACK_NAME}" "$NC"
        echo ""
        
        exit 1
    fi
}

# Handle script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Run main function
main "$@"
