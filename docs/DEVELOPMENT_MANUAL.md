# ThothAI - Development & Deployment Manual

This manual provides a comprehensive, "in-action" guide for developers and system administrators working with ThothAI. It covers the entire lifecycle from local development to production deployment on Docker Swarm.

---

## 🏗️ Architecture Overview

ThothAI is designed as a microservices architecture:
- **Backend**: Django (Python) - Core API and business logic.
- **Frontend**: Next.js (Node.js/React) - User interface.
- **SQL Generator**: FastAPI (Python/PydanticAI) - Dedicated AI agent service.
- **Mermaid Service**: Standalone service for diagram generation.
- **Infrastructure**: Qdrant (Vector DB), Postgres (App DB - optional), Nginx (Proxy).

1.  **Single Docker**: All services run in containers via Docker Compose.
2.  **Swarm**: Distributed deployment with replicas, secrets, and overlay networks.

---

## 📋 Prerequisites

### Required Software
- **Python**: 3.9+ (Python 3.11+ recommended)
- **Node.js**: 20+ (with npm)
- **uv**: Python package manager ([Installation](https://docs.astral.sh/uv/getting-started/))
- **Docker**: Desktop or Engine (for Docker and Swarm deployments)

### Recommended Tools
- **Git**: For version control
- **docker-compose**: Usually bundled with Docker Desktop

---

---

## 🛠️ Local Development (Docker-based)

For development, we use Docker Compose to run the entire stack. This ensures environment parity and simplifies setup.

## 📦 Part 2: Working with Docker Images

Before deploying to production (Swarm) or testing a full containerized setup, you must build the Docker images.

### Understanding Docker Configuration Files

- **`docker-compose.yml`**: Builds images from local source (`build: .`). Used for standard deployments.
- **`docker-compose-hub.yml`**: Uses pre-built images from registry (`image: ...`). Used for pulling from Docker Hub.

### Building and Pushing Images

We use unified scripts to handle **multi-platform builds** (linux/amd64 and linux/arm64) using **Docker Buildx**. This ensures that images built on a Mac ARM work perfectly on Windows Intel servers and vice-versa.

#### Command Syntax

**Bash:**
```
./push.sh <REGISTRY_URL> <VERSION> [OPTIONS]
```

**PowerShell:**
```
.\push.ps1 -RegistryUrl <REGISTRY_URL> -Version <VERSION> [OPTIONS]
```

#### Available Options

| Option | Bash | PowerShell | Description |
|--------|------|------------|-------------|
| No cache | `--no-cache` | `-NoCache` | Build without using cache |
| Push only | `--push-only` | `-PushOnly` | Skip build, push existing images only |
| Platforms | `--platforms` | `-Platforms` | Target platforms (default: `linux/amd64,linux/arm64`) |
| Help | `--help` | N/A | Show usage information |

#### Examples

**Mac/Linux:**
```bash
# Standard: Build AND Push to registry
./push.sh registry.example.com/my-org/thothai 1.0.0

# Build with no cache (clean build)
./push.sh registry.example.com/my-org/thothai 1.0.0 --no-cache

# Push only (images already built locally)
./push.sh registry.example.com/my-org/thothai 1.0.0 --push-only

# For local Swarm testing (no registry push needed)
docker compose build
```

**Windows:**
```powershell
# Standard: Build AND Push to registry
.\push.ps1 -RegistryUrl "registry.example.com/my-org/thothai" -Version "1.0.0"

# Build with no cache
.\push.ps1 -RegistryUrl "registry.example.com/my-org/thothai" -Version "1.0.0" -NoCache

# Push only (images already built)
.\push.ps1 -RegistryUrl "registry.example.com/my-org/thothai" -Version "1.0.0" -PushOnly
```

---

## 🚀 Part 3: Single-Node Deployment (Docker Compose)

This approach runs the entire stack in containers on a single machine. Ideal for staging servers or simple deployments.

### When to Use Each Option

- **`--pull`** (default): Pull pre-built images from Docker Hub - **recommended for production-like testing**
- **`--build`**: Build images locally - use when testing local code changes
- **`--clean-cache`**: Force clean build - use after major dependency changes

### Option A: Deploy from Docker Hub (Recommended)

This pulls efficient, pre-built images and simulates the exact user experience.

**Mac/Linux:**
```bash
# Standard installation (pulls from Docker Hub)
./install.sh

# Or explicitly specify pull
./install.sh --pull
```

**Windows:**
```powershell
# Standard installation
.\install.ps1

# Or explicitly specify pull
.\install.ps1 -Pull
```

### Option B: Deploy from Local Source

This builds images on the fly. Good for verifying that your local changes work in containers.

**Mac/Linux:**
```bash
# Build images locally
./install.sh --build

# Clean build (rebuild from scratch)
./install.sh --build --clean-cache
```

**Windows:**
```powershell
# Build images locally
.\install.ps1 -Build

# Clean build
.\install.ps1 -Build -CleanCache
```

### Additional Options

**Remove All Resources:**

**Mac/Linux:**
```bash
# Remove all ThothAI Docker resources
./install.sh --prune

# Force prune (skip confirmation)
./install.sh --prune --force
```

**Windows:**
```powershell
# Remove all resources
.\install.ps1 -Prune

# Force prune
.\install.ps1 -Prune -Force
```

### Access Points

After successful deployment:
- **Frontend**: `http://localhost:3040`
- **Backend Admin**: `http://localhost:8040/admin`
- **SQL Generator API**: `http://localhost:8020`
- **Qdrant**: `http://localhost:6334`

---

## 🐝 Part 4: Docker Swarm Deployment (Production)

Swarm is the target for production. It supports secrets, configs, rolling updates, and multi-node scaling.

### Key Concepts

- **Stack**: Defined in `docker-stack.yml`
- **Secrets**: API keys (from `config.yml.local`) are injected securely as Docker Secrets
- **Configs**: Environmental configs (`.env.docker`) are injected as Docker Configs
- **Swarm Config**: Port mappings and settings defined in `swarm_config.env`

> [!IMPORTANT]
> **Re-deploying Swarm**: If you already have an active swarm stack, before running `./install-swarm` (or `.ps1`), you **must** remove the existing stack:
> `docker stack rm thothai-swarm`

### Scenario A: Local Swarm (Testing Production)

You can run a single-node Swarm on your laptop to test production deployment using either official images or local builds.

**Method 1: Using Official Images (Fastest)**

**Mac/Linux:**
```bash
# 1. Initialize Swarm
docker swarm init

# 2. Deploy (script will pull images automatically)
./install-swarm.sh
```

**Windows:**
```powershell
# 1. Initialize Swarm
docker swarm init

# 2. Deploy
.\install-swarm.ps1
```

**Method 2: Using Local Builds (For Development)**
```bash
# 1. Initialize Swarm
docker swarm init

# 2. Build and tag images locally
docker compose build

# 3. Deploy
./install-swarm.sh --skip-pull
```

**Windows (Method 2 Example):**
```powershell
# 1. Initialize Swarm
docker swarm init

# 2. Build images locally
docker compose build

# 3. Deploy Stack
.\install-swarm.ps1 -SkipPull
```

### Scenario B: Remote Swarm (Production Server)

Deploy to a remote Swarm cluster directly from your local machine using SSH tunneling. You can either use official images from Docker Hub or your own custom-built images.

**Prerequisites:**
- SSH access to the manager node (`user@server-ip`)
- `swarm_config.env` configured with the correct `DOCKER_USERNAME`
- SSH key file (default: `~/.ssh/id_rsa`)

#### Path 1: Using Official Images (Recommended for Quick Installation)
If you want to install ThothAI using the official images from Docker Hub, you do **not** need to build or push anything locally. 

**Mac/Linux:**
```bash
# 1. Ensure DOCKER_USERNAME=tylconsulting in swarm_config.env
# 2. Deploy to Remote Server
./install-swarm.sh --server user@192.168.1.100
```

**Windows:**
```powershell
# 1. Ensure DOCKER_USERNAME=tylconsulting in swarm_config.env
# 2. Deploy to Remote Server
.\install-swarm.ps1 -Server "user@192.168.1.100"
```

#### Path 2: Using Custom Images (For Developers)
If you have modified the code and want to deploy your own version, you must build and push the images to a registry reachable by the server.

**Mac/Linux:**
```bash
# 1. Build and Push images to your registry
# Ensure DOCKER_USERNAME in swarm_config.env matches your registry namespace
./push.sh my-registry.com/thothai 1.0.0

# 2. Deploy to Remote Server
./install-swarm.sh --server user@192.168.1.100
```

**Windows (Custom Images Example):**
```powershell
# 1. Push images to registry
.\push.ps1 -RegistryUrl "my-registry.com/thothai" -Version "1.0.0"

# 2. Deploy to Remote Server
.\install-swarm.ps1 -Server "user@192.168.1.100"
```

> [!TIP]
> **DOCKER_USERNAME**: In `swarm_config.env`, this variable determines which images are pulled. 
> - For official images, use `tylconsulting`.
> - For custom images, use your Docker Hub username or your private registry URL/namespace.

### Advanced Options

| Option | Bash | PowerShell | Description |
|--------|------|------------|-------------|
| Remote deploy | `--server <SSH_STRING>` | `-Server <SSH_STRING>` | Deploy to remote via SSH |
| SSH port | `--port <PORT>` | `-Port <PORT>` | Custom SSH port (default: 22) |
| SSH key | `--key <PATH>` | `-Key <PATH>` | Path to SSH private key |
| Skip pull | `--skip-pull` | `-SkipPull` | Don't pull images from registry |
| Skip secrets | `--skip-secrets` | `-SkipSecrets` | Don't recreate secrets/configs |
| Remove stack | `--prune` | `-Prune` | Remove stack and resources |

### Managing the Swarm

Common operations for maintenance (Standard Docker commands work on all platforms):

```bash
# Check stack status
docker stack ps thothai-swarm

# View service logs
docker service logs -f thothai-swarm_backend

# Scale a service
docker service scale thothai-swarm_sql-generator=3

# Update a service
docker service update --image my-registry.com/thothai/thoth-backend:1.1.0 thothai-swarm_backend
```

**Remove Stack:**

**Mac/Linux:**
```bash
./install-swarm.sh --prune
```

**Windows:**
```powershell
.\install-swarm.ps1 -Prune
```

---

## 🔧 Port Reference

Different deployment modes use different port configurations:

| Service | Local Dev | Docker Compose | Docker Swarm |
|---------|-----------|----------------|--------------|
| **Frontend** | 3200 | 3040 | 7001 |
| **Backend** | 8200 | 8040 | 7002 |
| **SQL Generator** | 8180 | 8020 | 7003 |
| **Mermaid Service** | 8003 | 8004 | 7004 |
| **Qdrant** | 6333 | 6334 | 7005 |
| **Web Proxy** | - | - | 7000 |

**Notes:**
- Local Dev uses higher ports to avoid conflicts with system services
- Docker Compose uses 30xx/80xx ranges
- Docker Swarm uses 70xx range (configurable in `swarm_config.env`)
- Web Proxy (Nginx) is only used in Swarm deployments

---

## 🩺 Troubleshooting

### Port Conflicts

**Problem**: Service fails to start due to port already in use.

**Solution:**
```bash
# Mac/Linux - Find process using port
lsof -i :8200

# Kill the process
kill -9 <PID>

# Windows
netstat -ano | findstr :8200
taskkill /PID <PID> /F
```

### Docker Login Issues

**Problem**: `push.sh` or `push.ps1` fails with authentication error.

**Solution:**
```bash
# Login to Docker Hub
docker login

# Login to custom registry
docker login registry.example.com
```

### Permission Errors (Linux)

**Problem**: Docker commands require sudo.

**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again, or run:
newgrp docker
```

### Service Not Starting

**Problem**: Backend/Frontend/SQL Generator doesn't start.

**Check logs:**

**Mac/Linux:**
```bash
# Docker Compose
docker compose logs backend
docker compose logs frontend

# Docker Swarm
docker service logs thothai-swarm_backend
```

**Windows:**
```powershell
# Docker Compose
docker compose logs backend
docker compose logs frontend

# Docker Swarm
docker service logs thothai-swarm_backend
```

**Common causes:**
- Missing `config.yml.local`
- Invalid API keys
- Port conflicts
- Missing dependencies (run `uv sync` or `npm install`)

### Database Connection Errors

**Problem**: Backend can't connect to Qdrant or Postgres.

**Solution:**

**Mac/Linux:**
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check Qdrant health
curl http://localhost:6333/health  # Local dev
curl http://localhost:6334/health  # Docker Compose
curl http://localhost:7005/health  # Swarm
```

**Windows:**
```powershell
# Check if Qdrant is running
docker ps | Select-String qdrant

# Check Qdrant health
Invoke-WebRequest -Uri http://localhost:6333/health
```

### Clean Slate Restart

If everything seems broken:

```bash
# Stop all services
docker compose down

# Remove all ThothAI containers and volumes
./install.sh --prune --force  # Docker Compose
./install-swarm.sh --prune    # Swarm

# Restart from scratch
./install.sh    # Docker Compose
```

---

## 📄 Reference: Script Map

| Task | Mac/Linux | Windows | Notes |
|------|-----------|---------|-------|
| **Local Dev Setup & Start** | `./start-all.sh` | `.\start-all.ps1` | Handles all local dependencies |
| **Docker Compose Deploy** | `./install.sh` | `.\install.ps1` | Use `--build` for local images |
| **Build & Push Images** | `./push.sh` | `.\push.ps1` | Required before Swarm deploy |
| **Deploy Swarm** | `./install-swarm.sh` | `.\install-swarm.ps1` | Use `--server` for remote |
| **Remove Stack** | `./install-swarm.sh --prune` | `.\install-swarm.ps1 -Prune` | Clean removal |
| **Data Management** | `python scripts/data-exchange-cli.py` | `python scripts/data-exchange-cli.py` | Volume management |

---

## 🎯 Quick Start Cheat Sheet

### First Time Setup

**Mac/Linux:**
```bash
# 1. Clone repository
git clone <repo-url> && cd ThothAI

# 2. Configure
cp config.yml config.yml.local

# 3. Start local development
./start-all.sh
```

**Windows:**
```powershell
# 1. Clone repository
git clone <repo-url>; cd ThothAI

# 2. Configure
Copy-Item config.yml config.yml.local

# 3. Start local development
.\start-all.ps1
```

### Docker Compose Deployment

**Mac/Linux:**
```bash
# Pull and deploy
./install.sh

# Or build locally
./install.sh --build
```

**Windows:**
```powershell
# Pull and deploy
.\install.ps1

# Or build locally
.\install.ps1 -Build
```

### Production Swarm Deployment

**Mac/Linux:**
```bash
# 1. Build and push images
./push.sh my-registry.com/thothai 1.0.0

# 2. Deploy to production server
./install-swarm.sh --server user@production-server
```

**Windows:**
```powershell
# 1. Build and push images
.\push.ps1 -RegistryUrl "my-registry.com/thothai" -Version "1.0.0"

# 2. Deploy to production server
.\install-swarm.ps1 -Server "user@production-server"
```

---

*Copyright (c) 2025 Marco Pancotti*
*This file is part of ThothAI and is released under the Apache License 2.0.*
