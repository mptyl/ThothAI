# ThothAI Installation & Uninstallation Test Plan

> Comprehensive step-by-step guide for testing installation/uninstallation across all deployment scenarios.

---

## Port Reference

| Service        | Port |
|----------------|------|
| Frontend       | 3040 |
| Backend (Nginx)| 8040 |
| SQL Generator  | 8020 |
| Qdrant         | 6333 |
| Mermaid        | 8003 |

---

## Pre-Requisites

### Common Prerequisites
- Docker Desktop installed and running
- uv package manager installed (`pip install uv`)
- Git installed

### Port Cleanup Commands

```bash
# Check what's using a port
lsof -i :8040

# Kill process on specific ports
lsof -ti:8040 | xargs kill -9
lsof -ti:3040 | xargs kill -9
lsof -ti:8020 | xargs kill -9
lsof -ti:6333 | xargs kill -9

# Kill all ThothAI-related processes
pkill -f "manage.py runserver"
pkill -f "sql_generator/main.py"
pkill -f "next dev"
docker stop thoth-qdrant-local 2>/dev/null
```

---

## 1. LOCAL DEVELOPMENT

### 1.1 Manual Installation

```bash
# Prerequisites
cd /path/to/ThothAI

# 1. Setup Backend
cd backend
uv sync
cd ..

# 2. Setup SQL Generator
cd frontend/sql_generator
uv sync
cd ../..

# 3. Setup Frontend
cd frontend
npm install
cd ..

# 4. Configure environment
cp .env.local.template .env.local
nano .env.local  # Add API keys

# 5. Start Qdrant manually
mkdir -p qdrant_storage_local
docker run -d --name thoth-qdrant-local -p 6333:6333 \
  -v $(pwd)/qdrant_storage_local:/qdrant/storage qdrant/qdrant:latest

# 6. Start Backend (terminal 1)
cd backend && source .venv/bin/activate
python manage.py migrate --run-syncdb
python manage.py runserver 8040

# 7. Start SQL Generator (terminal 2)
cd frontend/sql_generator && source .venv/bin/activate
export DJANGO_SERVER=http://localhost:8040
export VECTOR_DB_HOST=localhost
uv run python main.py

# 8. Start Frontend (terminal 3)
cd frontend
export DJANGO_SERVER=http://localhost:8040
export SQL_GENERATOR_URL=http://localhost:8020
npm run dev
```

### 1.2 Shell Script Installation

```bash
# Start all services
./start-all.sh

# Services will be available at:
# - Frontend: http://localhost:3040
# - Backend: http://localhost:8040
# - SQL Generator: http://localhost:8020
```

### 1.3 CLI Installation (N/A for Local)

> CLI does not support local development mode. Use shell scripts.

---

### 1.4 Manual Uninstallation (Local)

```bash
# Kill backend
pkill -f "manage.py runserver"

# Kill SQL Generator
pkill -f "sql_generator/main.py"

# Kill Frontend
pkill -f "next dev"

# Stop Qdrant
docker stop thoth-qdrant-local
docker rm thoth-qdrant-local

# Optional: Clean data
rm -rf backend/db.sqlite3
rm -rf qdrant_storage_local/
```

### 1.5 Shell Script Uninstallation

```bash
./stop-all.sh
```

---

## 2. DOCKER COMPOSE

### 2.1 Manual Installation

```bash
cd /path/to/ThothAI

# 1. Configure
cp .env.docker.template .env.docker
nano .env.docker  # Set: DEPLOYMENT_MODE=compose, API keys

# 2. Create network
docker network create thoth-network

# 3. Create volumes
docker volume create thoth-backend-static
docker volume create thoth-backend-media
docker volume create thoth-frontend-cache
docker volume create thoth-qdrant-data
docker volume create thoth-secrets
docker volume create thoth-shared-data
docker volume create thoth-data-exchange

# 4. Start services
docker compose up -d

# 5. Check status
docker compose ps
```

### 2.2 Shell Script Installation

```bash
# 1. Configure
cp .env.docker.template .env.docker
nano .env.docker  # Set: DEPLOYMENT_MODE=compose, API keys

# 2. Start
./docker-up.sh

# Services available at:
# - Frontend: http://localhost:3040
# - Backend: http://localhost:8040
```

### 2.3 CLI Installation

```bash
# 1. Install CLI
pip install thothai-cli  # or: uv pip install thothai-cli

# 2. Initialize project (only first time, in empty directory)
mkdir my-thothai && cd my-thothai
thothai init

# 3. Configure
nano .env.docker  # Add API keys

# 4. Start
thothai up

# 5. Check status
thothai status
```

---

### 2.4 Manual Uninstallation (Compose)

```bash
# Stop containers
docker compose down

# With volume cleanup (removes all data!)
docker compose down -v

# Full cleanup
docker network rm thoth-network 2>/dev/null || true
docker volume ls -q | grep "thoth" | xargs -r docker volume rm
```

### 2.5 Shell Script Uninstallation

```bash
# Stop only
./docker-down.sh

# Stop and prune volumes
./docker-down.sh prune
```

### 2.6 CLI Uninstallation

```bash
# Stop only
thothai down

# Stop and prune all artifacts
thothai prune --yes

# Prune without removing volumes
thothai prune --yes --no-volumes
```

---

## 3. DOCKER SWARM

### 3.1 Manual Installation

```bash
cd /path/to/ThothAI

# 1. Initialize swarm (if not already)
docker swarm init

# 2. Configure
cp .env.docker.template .env.docker
nano .env.docker  # Set: DEPLOYMENT_MODE=swarm, API keys

cp swarm_config.env.template swarm_config.env
nano swarm_config.env  # Set: STACK_NAME, ports

# 3. Source configuration
source .env.docker
source swarm_config.env

# 4. Create overlay network
STACK=${STACK_NAME:-thoth-swarm}
docker network create --driver overlay --attachable ${STACK}_thoth-network

# 5. Create secrets
docker secret create ${STACK}_thoth_env_config .env.docker

# 6. Create configs
docker config create ${STACK}_thoth_env_docker .env.docker

# 7. Deploy stack
docker stack deploy -c docker-stack.yml $STACK

# 8. Check status
docker stack services $STACK
docker stack ps $STACK
```

### 3.2 Shell Script Installation

```bash
# 1. Configure
cp .env.docker.template .env.docker
nano .env.docker  # Set: DEPLOYMENT_MODE=swarm, API keys

# 2. Initialize swarm (if needed)
docker swarm init

# 3. Start
./docker-up.sh

# Check status
docker stack services thoth-swarm
```

### 3.3 CLI Installation

```bash
# 1. Configure .env.docker with DEPLOYMENT_MODE=swarm

# 2. Deploy locally
thothai swarm deploy

# 3. Deploy to remote server
thothai swarm deploy --server user@hostname

# 4. Check status
thothai swarm status
thothai swarm ps
```

---

### 3.4 Manual Uninstallation (Swarm)

```bash
STACK=${STACK_NAME:-thoth-swarm}

# Remove stack
docker stack rm $STACK

# Wait for removal
sleep 10

# Remove secrets
docker secret rm ${STACK}_thoth_env_config 2>/dev/null || true

# Remove configs  
docker config rm ${STACK}_thoth_env_docker 2>/dev/null || true

# Remove network
docker network rm ${STACK}_thoth-network 2>/dev/null || true

# Remove volumes (optional - removes data!)
docker volume ls -q | grep "thoth" | xargs -r docker volume rm
```

### 3.5 Shell Script Uninstallation

```bash
# Stop only
./docker-down.sh

# Stop and prune volumes
./docker-down.sh prune
```

### 3.6 CLI Uninstallation

```bash
# Stop only
thothai swarm down

# Full cleanup (local)
thothai swarm prune --yes

# Full cleanup (remote)
thothai swarm prune --server user@hostname --yes

# Keep volumes
thothai swarm prune --yes --no-volumes
```

---

## 4. COMPLETE CLEANUP

### Full System Cleanup

```bash
# Stop all ThothAI services
./stop-all.sh 2>/dev/null || true
./docker-down.sh prune 2>/dev/null || true

# Remove all ThothAI containers
docker ps -a | grep thoth | awk '{print $1}' | xargs -r docker rm -f

# Remove all ThothAI volumes
docker volume ls -q | grep "thoth" | xargs -r docker volume rm

# Remove all ThothAI networks
docker network ls | grep thoth | awk '{print $1}' | xargs -r docker network rm

# Remove all ThothAI secrets (Swarm)
docker secret ls 2>/dev/null | grep thoth | awk '{print $1}' | xargs -r docker secret rm

# Remove all ThothAI configs (Swarm)
docker config ls 2>/dev/null | grep thoth | awk '{print $1}' | xargs -r docker config rm

# Kill any lingering processes
lsof -ti:8040,3040,8020,6333 | xargs -r kill -9 2>/dev/null || true

# Clean local data (optional)
rm -rf backend/db.sqlite3
rm -rf qdrant_storage_local/
rm -rf qdrant_storage/
```

---

## 5. VERIFICATION CHECKLIST

### After Installation

- [ ] Frontend accessible at http://localhost:3040
- [ ] Backend accessible at http://localhost:8040/admin
- [ ] SQL Generator responding at http://localhost:8020/health
- [ ] Qdrant responding at http://localhost:6333
- [ ] Can login with demo/demo1234
- [ ] Can execute a test query

### After Uninstallation

- [ ] No thoth containers running: `docker ps | grep thoth`
- [ ] No thoth volumes (if pruned): `docker volume ls | grep thoth`
- [ ] No processes on ports: `lsof -i :8040,3040,8020,6333`
- [ ] No thoth networks: `docker network ls | grep thoth`
