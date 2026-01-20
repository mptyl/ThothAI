#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Start ThothAI - Compose or Swarm based on DEPLOYMENT_MODE

set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

# Check .env.docker
if [ ! -f .env.docker ]; then
    echo "Error: .env.docker not found"
    echo "Copy .env.docker.template to .env.docker and configure it"
    exit 1
fi

source .env.docker

# Check Docker daemon
echo "Checking Docker daemon..."
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker daemon is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi
echo "  Docker daemon is running"

# Kill conflicting ports (but skip Docker processes)
echo "Checking for port conflicts..."
for port in ${WEB_PORT:-8040} ${FRONTEND_PORT:-3040} ${SQL_GENERATOR_PORT:-8020} ${QDRANT_PORT:-6333}; do
    pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "  Found process(es) on port $port"
        for pid in $pids; do
            proc_name=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
            # Skip Docker-related processes
            if [[ "$proc_name" != *"docker"* ]] && [[ "$proc_name" != *"com.docker"* ]]; then
                echo "    Killing non-Docker process $pid ($proc_name)"
                kill -9 $pid 2>/dev/null || true
            else
                echo "    Skipping Docker process $pid ($proc_name)"
            fi
        done
    fi
done

MODE=${DEPLOYMENT_MODE:-compose}

# Stop local dev services ONLY if we're going to use Docker
# Use more specific patterns to avoid killing Docker processes
echo "Stopping local development services (if running)..."

# Check and stop local backend (only if running on our port)
if pgrep -f "python.*manage\.py runserver.*${WEB_PORT:-8040}" > /dev/null 2>&1; then
    pkill -f "python.*manage\.py runserver.*${WEB_PORT:-8040}" 2>/dev/null || true
    echo "  Stopped local backend"
fi

# Check and stop local SQL generator
if pgrep -f "python.*sql_generator/main\.py" > /dev/null 2>&1; then
    pkill -f "python.*sql_generator/main\.py" 2>/dev/null || true
    echo "  Stopped local SQL generator"
fi

# Stop local Qdrant container (this is safe - it's our container)
if docker ps --format '{{.Names}}' | grep -q 'thoth-qdrant-local'; then
    docker stop thoth-qdrant-local 2>/dev/null || true
    echo "  Stopped local Qdrant container"
fi

if [ "$MODE" = "swarm" ]; then
    echo "Deploying to Docker Swarm..."
    
    # Export all variables from env files for stack interpolation
    set -a
    [ -f swarm_config.env ] && source swarm_config.env
    [ -f .env.docker ] && source .env.docker
    set +a
    
    # Standardize STACK name
    STACK=${STACK_NAME:-thoth-swarm}
    echo "  Using stack name: $STACK"
    
    # Ensure overlay network exists
    NETWORK_NAME="${STACK}_thoth-network"
    if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
        echo "  Creating overlay network: $NETWORK_NAME"
        docker network create --driver overlay --attachable $NETWORK_NAME
    fi
    
    # Create/update secrets
    echo "  Managing Docker Secrets for $STACK..."
    
    # 1. Environment config secret
    SECRET_ENV="${STACK}_thoth_env_config"
    docker secret rm $SECRET_ENV 2>/dev/null || true
    docker secret create $SECRET_ENV .env.docker >/dev/null
    
    # 2. Config.yml.local secret (DEPRECATED - Removed)
    # SECRET_YML="${STACK}_thoth_config_yml"
    # if [ -f config.yml.local ]; then
    #     docker secret rm $SECRET_YML 2>/dev/null || true
    #     docker secret create $SECRET_YML config.yml.local >/dev/null
    # else
    #     echo "  Warning: config.yml.local not found, skipping secret creation"
    # fi

    
    # Create/update configs
    echo "  Managing Docker Configs for $STACK..."
    CONFIG_ENV="${STACK}_thoth_env_docker"
    docker config rm $CONFIG_ENV 2>/dev/null || true
    docker config create $CONFIG_ENV .env.docker >/dev/null

    echo "  Deploying stack: $STACK"
    docker stack deploy -c docker-stack.yml $STACK
    echo "Deployed: docker stack services $STACK"
else
    echo "Starting Docker Compose..."
    if [ "${BUILD_MODE:-hub}" = "build" ]; then
        docker compose up -d --build
    else
        docker compose up -d
    fi
    echo "Started: http://localhost:${WEB_PORT:-8040}"
fi
