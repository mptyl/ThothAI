#!/usr/bin/env bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

# Reset ThothAI Docker Swarm environment to Day 0

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

# 1. Loading configurations
print_header "Loading configurations"
if [ -f .env.docker ]; then
    set -a; source .env.docker; set +a
else
    echo -e "${RED}Error: .env.docker not found${NC}"
    exit 1
fi

[ -f swarm_config.env ] && { set -a; source swarm_config.env; set +a; }

STACK=${STACK_NAME:-thothai-swarm}

# 2. Removing Stack
print_header "Removing Stack: $STACK"
CMD="docker stack rm $STACK"
print_manual "$CMD"
$CMD || true

echo "Waiting for stack resources to be released..."
sleep 10

# 3. Removing Secrets and Configs
print_header "Cleaning Secrets and Configs"
RESOURCES=(
    "${STACK}_thoth_env_config"
    "${STACK}_thoth_env_docker"
)

for res in "${RESOURCES[@]}"; do
    if docker secret ls --format '{{.Name}}' | grep -q "^${res}$"; then
        CMD="docker secret rm $res"
        print_manual "$CMD"
        $CMD
    fi
    if docker config ls --format '{{.Name}}' | grep -q "^${res}$"; then
        CMD="docker config rm $res"
        print_manual "$CMD"
        $CMD
    fi
done

# 4. Cleaning Network
print_header "Cleaning Network"
NETWORK_NAME="${STACK}_thoth-network"
if docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
    CMD="docker network rm $NETWORK_NAME"
    print_manual "$CMD"
    $CMD || echo "Network might be still in use, skipping removal."
fi

# 5. Database Schema Reset (Day 0)
print_header "Resetting Database Schema"

# Database Configuration
USER="${DB_USER:-thoth_user}"
DB="${DB_NAME:-thoth_db}"
HOST="${DB_HOST:-localhost}" # Use localhost if external, 'db' wont work here as stack is down
PASSWORD="${DB_PASSWORD:-thoth_pass}"
PORT="${DB_PORT:-5432}"
SCHEMA="${DB_SCHEMA:-thoth_db}"

# Correct host for reset: if it was 'db' in swarm, it must be accessed via host or IP from outside
if [ "$HOST" == "db" ]; then
    echo -e "${YELLOW}Warning: DB_HOST was 'db' (internal Swarm). Resolving to 'localhost' for external reset.${NC}"
    HOST="localhost"
    # Port might need to be 5443 if using the one mapped in local compose for convenience, 
    # but for Swarm we should use the host port defined in swarm_env if any.
fi

SQL_CMD="DROP SCHEMA IF EXISTS $SCHEMA CASCADE; CREATE SCHEMA $SCHEMA;"

# Detect if we need special handling for host.docker.internal
EXTRA_HOSTS=""
if [[ "$HOST" == "host.docker.internal" ]]; then
    EXTRA_HOSTS="--add-host=host.docker.internal:host-gateway"
fi

echo "  Executing schema reset on $HOST:$PORT..."
CMD="docker run --rm $EXTRA_HOSTS -e PGPASSWORD=$PASSWORD postgres:16-alpine psql -h $HOST -p $PORT -U $USER -d $DB -c \"$SQL_CMD\""
print_manual "$CMD"

if eval $CMD; then
    echo -e "${GREEN}✓ Schema $SCHEMA reset successfully${NC}"
else
    echo -e "${RED}✗ Failed to reset schema. Check if DB is reachable and credentials are correct.${NC}"
fi

# 6. Cleaning Bind Mounts (Optional warning)
print_header "Data Persistence"
echo -e "${YELLOW}Manual Action Required:${NC} To completely wipe data, manually remove bind-mount directories:"
echo "  - ${THOTH_DATA_PATH:-.}/postgres_data"
echo "  - ${THOTH_DATA_PATH:-.}/qdrant_data"
echo "  - etc."

print_header "Cleanup Complete"
echo -e "${GREEN}Swarm environment $STACK has been reset to Day 0.${NC}"
