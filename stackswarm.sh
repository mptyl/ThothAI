#!/usr/bin/env bash
set -euo pipefail

# Default values (override by exporting env vars before running)
REGISTRY_URL="${REGISTRY_URL:-registry.uni.com/tylconsulting/thothai}"
VERSION="${VERSION:-0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-3040}"
BACKEND_PORT="${BACKEND_PORT:-8040}"
SQL_GENERATOR_PORT="${SQL_GENERATOR_PORT:-8020}"
MERMAID_SERVICE_PORT="${MERMAID_SERVICE_PORT:-8003}"
WEB_PORT="${WEB_PORT:-8040}"
STACK_FILE="${STACK_FILE:-docker-stack-simple.yml}"
STACK_NAME="${STACK_NAME:-thoth}"

echo "Using:"
echo "  REGISTRY_URL=$REGISTRY_URL"
echo "  VERSION=$VERSION"
echo "  FRONTEND_PORT=$FRONTEND_PORT"
echo "  BACKEND_PORT=$BACKEND_PORT"
echo "  SQL_GENERATOR_PORT=$SQL_GENERATOR_PORT"
echo "  MERMAID_SERVICE_PORT=$MERMAID_SERVICE_PORT"
echo "  WEB_PORT=$WEB_PORT"
echo "  STACK_FILE=$STACK_FILE"
echo "  STACK_NAME=$STACK_NAME"

# Export for docker stack variable substitution
export REGISTRY_URL VERSION FRONTEND_PORT BACKEND_PORT SQL_GENERATOR_PORT MERMAID_SERVICE_PORT WEB_PORT

docker stack deploy -c "$STACK_FILE" "$STACK_NAME"

echo "Deploy inviato. Controlla: docker stack services $STACK_NAME"
