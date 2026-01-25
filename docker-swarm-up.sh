#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}==== $1 ====${NC}"
}

print_manual() {
    echo -e "${YELLOW}Manual command:${NC} $1"
}

# 1. Initialization
print_header "Checking Docker Swarm status"
if ! docker info | grep -q "Swarm: active"; then
    echo "Swarm is not active. Initializing..."
    print_manual "docker swarm init"
    docker swarm init
else
    echo "✓ Swarm is active"
fi

# 2. Loading configurations
print_header "Loading configurations"
if [ ! -f .env.docker ]; then
    echo -e "${RED}Error: .env.docker not found${NC}"
    echo "Please run: cp .env.compose.template .env.docker"
    exit 1
fi

if [ ! -f swarm_config.env ]; then
    echo -e "${YELLOW}Warning: swarm_config.env not found. Using template defaults.${NC}"
    cp swarm_config.env.template swarm_config.env
fi

set -a
source .env.docker
source swarm_config.env
set +a
echo "✓ Configurations loaded"

# 3. Managing Network
STACK=${STACK_NAME:-thothai-swarm}
NETWORK_NAME="${STACK}_thoth-network"

print_header "Managing Network"
if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
    CMD="docker network create --driver overlay --attachable ${NETWORK_NAME}"
    print_manual "$CMD"
    $CMD
else
    echo "✓ Network $NETWORK_NAME already exists"
fi

# 4. Managing Secrets & Configs
print_header "Managing Secrets and Configs"

manage_resource() {
    local type=$1
    local name=$2
    local file=$3
    echo "Updating $type: $name"
    docker $type rm "$name" 2>/dev/null || true
    CMD="docker $type create $name $file"
    print_manual "$CMD"
    $CMD >/dev/null
}

manage_resource "secret" "${STACK}_thoth_env_config" ".env.docker"
manage_resource "config" "${STACK}_thoth_env_docker" ".env.docker"

# 5. Deployment
print_header "Deploying Stack"
export REGISTRY_URL="${DOCKER_REGISTRY:-tylconsulting}"
export IMAGE_VERSION="${IMAGE_VERSION:-latest}"

CMD="docker stack deploy -c docker-stack.yml $STACK"
print_manual "$CMD"
$CMD

print_header "Deployment Initiated"
echo -e "Access Point: ${GREEN}http://localhost:${WEB_PORT:-7010}${NC}"
echo -e "Check status: ${YELLOW}docker stack services $STACK${NC}"
