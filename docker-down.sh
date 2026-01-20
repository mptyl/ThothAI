#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Stop ThothAI

set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

PRUNE=${1:-}

if [ -f .env.docker ]; then
    source .env.docker
fi

MODE=${DEPLOYMENT_MODE:-compose}
STACK=${STACK_NAME:-thoth}

if [ "$MODE" = "swarm" ]; then
    docker stack rm $STACK
    
    if [ "$PRUNE" = "prune" ]; then
        echo "Waiting for stack removal..."
        sleep 10
        docker volume ls -q | grep "thoth" | xargs -r docker volume rm 2>/dev/null || true
        docker secret rm ${STACK}_env 2>/dev/null || true
    fi
else
    if [ "$PRUNE" = "prune" ]; then
        docker compose down -v
    else
        docker compose down
    fi
fi

echo "ThothAI stopped."
