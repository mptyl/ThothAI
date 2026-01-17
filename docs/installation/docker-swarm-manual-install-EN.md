# Manual Docker Swarm Installation - ThothAI

Copyright (c) 2025 Tyl Consulting di Pancotti Marco
This file is part of ThothAI and is released under the Apache License 2.0.
See the LICENSE.md file in the project root for full license information.

---

This guide describes how to install ThothAI on Docker Swarm without using the CLI, manually executing commands from a Linux terminal. Images will be pulled from Docker Hub.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [File Structure](#file-structure)
3. [Configuration](#configuration)
4. [Environment Preparation](#environment-preparation)
5. [Stack Deployment](#stack-deployment)
6. [Verification and Monitoring](#verification-and-monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Stack Removal](#stack-removal)

---

## Prerequisites

### Required Software

```bash
# Verify Docker is installed
docker --version

# Verify Docker Swarm is initialized
docker info | grep "Swarm:"
# If not initialized, run:
docker swarm init

# Verify envsubst (part of gettext)
which envsubst || sudo apt-get install -y gettext-base
```

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk | 20 GB | 50+ GB |

---

## File Structure

Create a working directory and download/create the necessary files:

```bash
mkdir -p /opt/thothai
cd /opt/thothai
```

Required files:
- `docker-stack.yml` - Docker stack template
- `config.yml.local` - Main configuration
- `swarm_config.env` - Ports and stack name configuration
- `.env.docker` - Environment variables (generated from configuration)

---

## Configuration

### 1. Create `swarm_config.env`

```bash
cat > swarm_config.env << 'EOF'
# ThothAI Docker Swarm Configuration
# -----------------------------------

# Docker Hub username for pulling images
DOCKER_USERNAME=tylconsulting

# Docker Swarm stack name
STACK_NAME=thothai-swarm

# Image version to download
VERSION=latest

# Port Configuration
# ------------------
WEB_PORT=7010           # Nginx gateway port (main entry point)
FRONTEND_PORT=7001      # Next.js frontend port
BACKEND_PORT=7002       # Django backend port
SQL_GENERATOR_PORT=7003 # FastAPI SQL Generator port
MERMAID_SERVICE_PORT=7004  # Mermaid service port
QDRANT_PORT=7005        # Qdrant vector database port
EOF
```

### 2. Create `config.yml.local`

```bash
cat > config.yml.local << 'EOF'
# ThothAI Configuration
# ---------------------

# Admin credentials
admin:
  username: admin
  email: admin@example.com
  password: CHANGE_THIS_PASSWORD

# AI Providers (configure at least one)
ai_providers:
  openai:
    enabled: true
    api_key: sk-INSERT_API_KEY
    model: gpt-4o
  
  # Optional providers
  gemini:
    enabled: false
    api_key: 
  anthropic:
    enabled: false
    api_key: 

# Embedding configuration
embeddings:
  provider: openai
  api_key: sk-INSERT_API_KEY
  model: text-embedding-3-large

# Docker settings
docker:
  deployment_mode: swarm
  stack_name: thothai-swarm

# Ports (must match swarm_config.env)
ports:
  nginx: 7010
  frontend: 7001
  backend: 8000
  sql_generator: 7003
EOF
```

### 3. Generate `.env.docker`

Create the Docker environment variables file:

```bash
cat > .env.docker << 'EOF'
# ThothAI Docker Environment
# Generated from configuration

# Admin
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=CHANGE_THIS_PASSWORD

# AI Providers
OPENAI_API_KEY=sk-INSERT_API_KEY
OPENAI_MODEL=gpt-4o

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-INSERT_API_KEY
EMBEDDING_MODEL=text-embedding-3-large

# Django settings
DJANGO_SECRET_KEY=$(openssl rand -hex 32)
DJANGO_DEBUG=False
ALLOWED_HOSTS=*
CORS_ALLOW_ALL_ORIGINS=True

# Service URLs (internal)
VECTOR_DB_HOST=thoth-qdrant
VECTOR_DB_PORT=6333
DJANGO_SERVER=http://backend:8000
SQL_GENERATOR_URL=http://sql-generator:8020

# Enabled databases
ENABLED_DATABASES=sqlite,postgresql,mariadb,sqlserver
EOF
```

> [!IMPORTANT]
> Replace all placeholder values (`CHANGE_THIS_PASSWORD`, `sk-INSERT_API_KEY`) with actual values.

---

## Environment Preparation

### 1. Load environment variables

```bash
cd /opt/thothai
set -a; source swarm_config.env; set +a
```

### 2. Create Docker volumes

```bash
# Required volumes for data persistence
docker volume create thoth-secrets
docker volume create thoth-backend-static
docker volume create thoth-backend-media
docker volume create thoth-frontend-cache
docker volume create thoth-qdrant-data
docker volume create thoth-shared-data
docker volume create thoth-data-exchange
docker volume create thoth-backend-db
docker volume create thoth-backend-secrets
docker volume create thoth-logs

echo "✓ Volumes created"
```

### 3. Create Secrets and Configs

Docker Swarm uses secrets and configs to manage sensitive data:

```bash
# Remove existing secrets/configs (ignore errors if they don't exist)
docker secret rm ${STACK_NAME}_thoth_env_config 2>/dev/null || true
docker secret rm ${STACK_NAME}_thoth_config_yml 2>/dev/null || true
docker config rm ${STACK_NAME}_thoth_env_docker 2>/dev/null || true

# Create new secrets
docker secret create ${STACK_NAME}_thoth_env_config .env.docker
docker secret create ${STACK_NAME}_thoth_config_yml config.yml.local

# Create config
docker config create ${STACK_NAME}_thoth_env_docker .env.docker

echo "✓ Secrets and configs created"
```

### 4. Pull images from Docker Hub

```bash
echo "Pulling images from Docker Hub..."

docker pull ${DOCKER_USERNAME}/thoth-backend:${VERSION}
docker pull ${DOCKER_USERNAME}/thoth-frontend:${VERSION}
docker pull ${DOCKER_USERNAME}/thoth-sql-generator:${VERSION}
docker pull ${DOCKER_USERNAME}/thoth-proxy:${VERSION}
docker pull ${DOCKER_USERNAME}/thoth-mermaid-service:${VERSION}
docker pull qdrant/qdrant:latest

echo "✓ All images pulled"
```

### 5. Download and prepare docker-stack.yml

```bash
# Download docker-stack.yml template from repository
curl -o docker-stack.yml \
  https://raw.githubusercontent.com/tylconsulting/thothai/main/cli/thothai-cli/src/thothai_cli/templates/docker-stack.yml

# Or copy it from source if available
```

### 6. Prepare the deployment file

The `docker-stack.yml` file contains variables that must be substituted:

```bash
# Export variables for envsubst
export DOCKER_USERNAME STACK_NAME VERSION
export WEB_PORT FRONTEND_PORT BACKEND_PORT SQL_GENERATOR_PORT MERMAID_SERVICE_PORT QDRANT_PORT

# Substitute variables in template
envsubst < docker-stack.yml > docker-stack-deploy.yml

# Important: replace secret/config names with stack prefix
sed -i "s/thothai-swarm_thoth_env_config/${STACK_NAME}_thoth_env_config/g" docker-stack-deploy.yml
sed -i "s/thothai-swarm_thoth_config_yml/${STACK_NAME}_thoth_config_yml/g" docker-stack-deploy.yml
sed -i "s/thothai-swarm_thoth_env_docker/${STACK_NAME}_thoth_env_docker/g" docker-stack-deploy.yml

echo "✓ Deployment file prepared: docker-stack-deploy.yml"
```

---

## Stack Deployment

### Execute the deployment

```bash
cd /opt/thothai

# Deploy the stack
docker stack deploy -c docker-stack-deploy.yml ${STACK_NAME}

echo "Stack '${STACK_NAME}' starting..."
```

### Wait for services to start

```bash
# Script to wait for all services to be ready
echo "Waiting for all services to start..."
MAX_WAIT=600  # 10 minutes
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Get replica status
    REPLICAS=$(docker stack services ${STACK_NAME} --format "{{.Replicas}}")
    ALL_READY=true
    
    for R in $REPLICAS; do
        CURRENT=$(echo $R | cut -d'/' -f1)
        DESIRED=$(echo $R | cut -d'/' -f2)
        if [ "$CURRENT" != "$DESIRED" ]; then
            ALL_READY=false
            break
        fi
    done
    
    if [ "$ALL_READY" = true ]; then
        echo ""
        echo "✓ All services are running!"
        break
    fi
    
    echo -n "."
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo ""
    echo "⚠ Timeout: some services may not be ready yet"
fi
```

---

## Verification and Monitoring

### Check service status

```bash
# List stack services
docker stack services ${STACK_NAME}

# Detailed task information per service
docker stack ps ${STACK_NAME}

# Logs for a specific service
docker service logs ${STACK_NAME}_backend --tail 100
docker service logs ${STACK_NAME}_frontend --tail 100
docker service logs ${STACK_NAME}_sql-generator --tail 100
```

### Application Access

Once all services are running:

| Service | URL |
|---------|-----|
| **Main App (Gateway)** | `http://SERVER_IP:7010` |
| **Direct Frontend** | `http://SERVER_IP:7001` |
| **Django Admin** | `http://SERVER_IP:7010/admin` |
| **Backend API** | `http://SERVER_IP:7010/api` |
| **SQL Generator** | `http://SERVER_IP:7003` |

---

## Troubleshooting

### Issue: Service doesn't start

```bash
# Check service logs
docker service logs ${STACK_NAME}_SERVICE_NAME --tail 200

# Check task status
docker service ps ${STACK_NAME}_SERVICE_NAME --no-trunc

# Force service update
docker service update --force ${STACK_NAME}_SERVICE_NAME
```

### Issue: Secrets not found

```bash
# Verify secrets exist
docker secret ls | grep ${STACK_NAME}

# Recreate if necessary
docker secret rm ${STACK_NAME}_thoth_env_config
docker secret create ${STACK_NAME}_thoth_env_config .env.docker
```

### Issue: Connection errors between services

```bash
# Verify overlay network exists
docker network ls | grep thoth

# Inspect the network
docker network inspect ${STACK_NAME}_thoth-network
```

### Issue: Backend not responding

```bash
# Backend has a long start_period (1200s) for first initialization
# Check logs to monitor progress
docker service logs -f ${STACK_NAME}_backend
```

---

## Stack Removal

### Remove the stack completely

```bash
# Load variables if not already loaded
source swarm_config.env

# Remove the stack
docker stack rm ${STACK_NAME}

echo "Waiting for services to be removed..."
sleep 10

# Remove secrets and configs
docker secret rm ${STACK_NAME}_thoth_env_config 2>/dev/null || true
docker secret rm ${STACK_NAME}_thoth_config_yml 2>/dev/null || true
docker config rm ${STACK_NAME}_thoth_env_docker 2>/dev/null || true

echo "✓ Stack removed"
```

### Also remove volumes (⚠️ WARNING: deletes all data)

```bash
# Wait for stack to be completely removed
sleep 15

# Remove volumes
docker volume rm thoth-secrets thoth-backend-static thoth-backend-media \
  thoth-frontend-cache thoth-qdrant-data thoth-shared-data \
  thoth-data-exchange thoth-backend-db thoth-backend-secrets thoth-logs

echo "✓ Volumes removed"
```

---

## References

- [Docker Swarm Documentation](https://docs.docker.com/engine/swarm/)
- [ThothAI GitHub Repository](https://github.com/tylconsulting/thothai)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
