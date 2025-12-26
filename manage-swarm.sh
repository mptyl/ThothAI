#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# Script di deployment automatizzato per ThothAI su Docker Swarm
# Supporta deployment locale e remoto con immagini da Docker Hub

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration Defaults (can be overridden by config file)
STACK_NAME="thothai-swarm"
BACKUP_DIR="/backup/thoth"

# Porte default per Docker Swarm
WEB_PORT="7010"
FRONTEND_PORT="7001"
BACKEND_PORT="7002"
SQL_GENERATOR_PORT="7003"
MERMAID_SERVICE_PORT="7004"
QDRANT_PORT="7005"

DOCKER_CMD="docker"

print_color() {
    echo -e "${2}${1}${NC}"
}

# Functions
check_prerequisites() {
    print_color "=== Check prerequisites ===" "$BLUE"
    
    # Check Docker
    if ! $DOCKER_CMD info > /dev/null 2>&1; then
        print_color "Error: Docker is not running or not reachable" "$RED"
        exit 1
    fi
}

load_config() {
    local config_file="swarm_config.env"
    
    if [ ! -f "$config_file" ]; then
        print_color "Warning: $config_file not found, using defaults" "$YELLOW"
        return
    fi
    
    # Source the configuration file
    set -a
    source "$config_file"
    set +a
    
    print_color "Configuration loaded from $config_file" "$GREEN"
}

backup_volumes() {
    print_color "=== Backup volumes ===" "$BLUE"
    
    BACKUP_PATH="$BACKUP_DIR/$(date +%Y%m%d_%H%M%S)"
    
    # Backup database
    print_color "Backup database..." "$YELLOW"
    $DOCKER_CMD run --rm \
        -v "${STACK_NAME}_thoth-backend-db":/data \
        -v "$BACKUP_PATH":/backup \
        alpine sh -c "mkdir -p /backup && tar czf /backup/backend-db.tar.gz -C /data . 2>/dev/null || true"
    
    # Backup Qdrant
    print_color "Backup Qdrant..." "$YELLOW"
    $DOCKER_CMD run --rm \
        -v "${STACK_NAME}_qdrant-data":/data \
        -v "$BACKUP_PATH":/backup \
        alpine sh -c "mkdir -p /backup && tar czf /backup/qdrant-data.tar.gz -C /data . 2>/dev/null || true"
    
    # Backup data-exchange (volume condiviso)
    print_color "Backup thoth-data-exchange..." "$YELLOW"
    $DOCKER_CMD run --rm \
        -v thoth-data-exchange:/data \
        -v "$BACKUP_PATH":/backup \
        alpine sh -c "mkdir -p /backup && tar czf /backup/data-exchange.tar.gz -C /data . 2>/dev/null || true"
    
    print_color "✓ Backup attempted in $BACKUP_PATH (on swarm node)" "$GREEN"
}

update_secrets() {
    print_color "=== Update Secrets ===" "$BLUE"
    
    # Remove old secrets if exist
    $DOCKER_CMD secret rm "${STACK_NAME}_thoth_env_config" 2>/dev/null || true
    $DOCKER_CMD secret rm "${STACK_NAME}_thoth_config_yml" 2>/dev/null || true
    
    # Create new secrets
    if [ -f ".env.docker" ]; then
        $DOCKER_CMD secret create "${STACK_NAME}_thoth_env_config" .env.docker
        print_color "✓ Created secret: ${STACK_NAME}_thoth_env_config" "$GREEN"
    else
        print_color "Warning: .env.docker not found, skipping secret creation" "$YELLOW"
    fi
    
    if [ -f "config.yml.local" ]; then
        $DOCKER_CMD secret create "${STACK_NAME}_thoth_config_yml" config.yml.local
        print_color "✓ Created secret: ${STACK_NAME}_thoth_config_yml" "$GREEN"
    else
        print_color "Warning: config.yml.local not found, skipping secret creation" "$YELLOW"
    fi
    
    print_color "✓ Secrets updated" "$GREEN"
}

update_configs() {
    print_color "=== Update Configs ===" "$BLUE"
    
    # Remove old configs if exist
    $DOCKER_CMD config rm "${STACK_NAME}_thoth_env_docker" 2>/dev/null || true
    
    # Create new configs
    if [ -f ".env.docker" ]; then
        $DOCKER_CMD config create "${STACK_NAME}_thoth_env_docker" .env.docker
        print_color "✓ Created config: ${STACK_NAME}_thoth_env_docker" "$GREEN"
    else
        print_color "Warning: .env.docker not found, skipping config creation" "$YELLOW"
    fi
    
    print_color "✓ Configs updated" "$GREEN"
}

prepare_stack_file() {
    print_color "=== Prepare Stack File ===" "$BLUE"
    
    if [ ! -f "docker-stack.yml" ]; then
        print_color "Error: docker-stack.yml not found" "$RED"
        exit 1
    fi
    
    # Set environment variables for envsubst
    export REGISTRY_URL="${DOCKER_USERNAME:-your-dockerhub-username}"
    export VERSION="${VERSION:-latest}"
    export WEB_PORT="$WEB_PORT"
    export FRONTEND_PORT="$FRONTEND_PORT"
    export BACKEND_PORT="$BACKEND_PORT"
    export SQL_GENERATOR_PORT="$SQL_GENERATOR_PORT"
    export MERMAID_SERVICE_PORT="$MERMAID_SERVICE_PORT"
    export QDRANT_PORT="$QDRANT_PORT"
    
    # Create docker-stack-swarm.yml with substituted values
    print_color "Creating docker-stack-swarm.yml with port substitutions..." "$YELLOW"
    if envsubst < docker-stack.yml > docker-stack-swarm.yml; then
        print_color "✓ docker-stack-swarm.yml created" "$GREEN"
    else
        print_color "✗ Failed to create docker-stack-swarm.yml" "$RED"
        exit 1
    fi
    
    # Update with stack-specific names
    sed -i.tmp "s/thoth_env_config/${STACK_NAME}_thoth_env_config/g" docker-stack-swarm.yml
    sed -i.tmp "s/thoth_config_yml/${STACK_NAME}_thoth_config_yml/g" docker-stack-swarm.yml
    sed -i.tmp "s/thoth_env_docker/${STACK_NAME}_thoth_env_docker/g" docker-stack-swarm.yml
    rm -f docker-stack-swarm.yml.tmp
    print_color "✓ Updated docker-stack-swarm.yml with stack-specific names" "$GREEN"
}

deploy_stack() {
    print_color "=== Deploy Stack ===" "$BLUE"
    
    print_color "Port configuration:" "$YELLOW"
    print_color "  Web (Proxy):        $WEB_PORT" "$NC"
    print_color "  Frontend:           $FRONTEND_PORT" "$NC"
    print_color "  Backend (via proxy): $BACKEND_PORT" "$NC"
    print_color "  SQL Generator:      $SQL_GENERATOR_PORT" "$NC"
    print_color "  Mermaid Service:    $MERMAID_SERVICE_PORT" "$NC"
    print_color "  Qdrant:             $QDRANT_PORT" "$NC"
    echo ""
    
    if [ "$DOCKER_CMD" != "docker" ]; then
        print_color "Deploy on remote host..." "$BLUE"
    fi
    
    # Create network if it doesn't exist
    print_color "Ensuring network exists..." "$YELLOW"
    if ! $DOCKER_CMD network ls | grep -q "${STACK_NAME}_thoth-network"; then
        print_color "Creating network ${STACK_NAME}_thoth-network..." "$YELLOW"
        $DOCKER_CMD network create --driver overlay --attachable "${STACK_NAME}_thoth-network"
        print_color "✓ Network created" "$GREEN"
    else
        print_color "✓ Network already exists" "$GREEN"
    fi
    echo ""

    # Deploy stack
    $DOCKER_CMD stack deploy -c docker-stack-swarm.yml "$STACK_NAME"
    
    print_color "✓ Deploy completed" "$GREEN"
}

wait_for_services() {
    print_color "=== Checking services status ===" "$BLUE"
    
    local max_wait=1200 # 20 minuti
    local elapsed=0
    
    while [ $elapsed -lt $max_wait ]; do
        local running=$($DOCKER_CMD stack services "$STACK_NAME" --format "{{.Replicas}}" | grep -v "0/0" | wc -l)
        local total=$($DOCKER_CMD stack services "$STACK_NAME" --format "{{.Replicas}}" | wc -l)
        
        # Check if all replicas are running
        local all_running=true
        if [ "$total" -eq 0 ]; then
              all_running=false
        else
            while IFS= read -r line; do
                if [[ $line != *"1/1"* && $line != *"2/2"* ]]; then
                    all_running=false
                    break
                fi
            done < <($DOCKER_CMD stack services "$STACK_NAME" --format "{{.Replicas}}")
        fi
        
        if [ "$all_running" = true ]; then
            print_color "✓ All services are running" "$GREEN"
            return 0
        fi
        
        print_color "Waiting for services... ($elapsed/$max_wait seconds)" "$YELLOW"
        sleep 10
        elapsed=$((elapsed + 10))
    done
    
    print_color "Timeout: Services not started in time" "$RED"
    return 1
}

show_services_status() {
    print_color "=== Services Status ===" "$BLUE"
    $DOCKER_CMD stack services "$STACK_NAME"
}

show_logs() {
    print_color "=== Backend Logs (last 20 lines) ===" "$BLUE"
    $DOCKER_CMD service logs --tail 20 "${STACK_NAME}_backend" 2>&1 || true
}

rollback() {
    print_color "=== Rollback ===" "$RED"
    
    $DOCKER_CMD service rollback "${STACK_NAME}_backend" 2>/dev/null || true
    $DOCKER_CMD service rollback "${STACK_NAME}_frontend" 2>/dev/null || true
    $DOCKER_CMD service rollback "${STACK_NAME}_sql-generator" 2>/dev/null || true
}

# Main execution
main() {
    # Parse arguments
    SKIP_BACKUP=false
    ROLLBACK_ONLY=false
    STATUS_ONLY=false
    LOGS_ONLY=false
    REMOTE_HOST=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --rollback-only)
                ROLLBACK_ONLY=true
                shift
                ;;
            --status-only)
                STATUS_ONLY=true
                shift
                ;;
            -H|--host)
                REMOTE_HOST="$2"
                DOCKER_CMD="docker -H $REMOTE_HOST"
                shift 2
                ;;
            --config)
                # Load config file (shell script sourcing)
                if [ -f "$2" ]; then
                    print_color "Loading config from $2" "$BLUE"
                    set -a
                    source "$2"
                    set +a
                else
                    print_color "Config file $2 not found" "$RED"
                    exit 1
                fi
                shift 2
                ;;
            *)
                print_color "Unknown option: $1" "$RED"
                echo ""
                echo "Options:"
                echo "  --skip-backup         Skip the backup of volumes"
                echo "  --rollback-only       Only execute the rollback"
                echo "  --status-only         Only show the services status"
                echo "  -H, --host <HOST>     Docker host remote (e.g. ssh://user@host)"
                echo "  --config <FILE>       Load port configuration from file"
                exit 1
                ;;
        esac
    done
    
    print_color "============================================" "$BLUE"
    print_color "  ThothAI - Deploy Automated Swarm" "$BLUE"
    print_color "============================================" "$BLUE"
    echo ""
    
    if [ "$ROLLBACK_ONLY" = true ]; then rollback; exit 0; fi
    if [ "$STATUS_ONLY" = true ]; then show_services_status; exit 0; fi
    if [ "$LOGS_ONLY" = true ]; then show_logs; exit 0; fi
    
    # Load configuration
    load_config
    
    print_color "Registry: $REGISTRY_URL" "$YELLOW"
    print_color "Version: $VERSION" "$YELLOW"
    print_color "Stack:    $STACK_NAME" "$YELLOW"
    echo ""
    
    if [ -n "$REMOTE_HOST" ]; then
        print_color "Remote host: $REMOTE_HOST" "$YELLOW"
        echo ""
    fi
    
    check_prerequisites
    
    if [ "$SKIP_BACKUP" = false ]; then
        backup_volumes
    fi
    
    update_secrets
    update_configs
    prepare_stack_file
    deploy_stack
    
    if ! wait_for_services; then
        print_color "Deploy failed. Executing rollback..." "$RED"
        rollback
        show_logs
        exit 1
    fi
    
    show_services_status
    rm -f docker-stack-swarm.yml
}

main "$@"
