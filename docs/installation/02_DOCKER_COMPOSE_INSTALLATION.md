# Docker Compose Installation Guide

This guide covers deploying ThothAI using **Docker Compose**. This is the standard method for running the complete stack in a containerized environment, suitable for both development and simple production server setups.

## Prerequisites

- **Docker Desktop** (Mac/Windows) or **Docker Engine** (Linux) installed.
- **Docker Compose V2** enabled.
- **Git** to clone the repository.

## 1. Initial Setup

### Clone and Prepare
```bash
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI
```

### Configuration
Everything is controlled by the `.env.docker` file. This file is **gitignored** to protect your secrets.

1.  **Create Configuration**:
    ```bash
    cp .env.compose.template .env.docker
    ```

2.  **Edit Settings**:
    Open `.env.docker` and configure:
    - **API Keys**: `OPENAI_API_KEY`, etc.
    - **Deployment Mode**: Ensure `DEPLOYMENT_MODE=compose` (default).
    - **Build Mode**:
        - `BUILD_MODE=hub` (Default): Pulls pre-built images from Docker Hub. Faster and stable.
        - `BUILD_MODE=build`: Builds images locally from your source code. Use this if you have modified the code.

3.  **Optional External Database**:
    By default, an internal PostgreSQL container is used (`POSTGRES_INTERNAL=true`).
    To use an external database (e.g., host machine Postgres or Cloud RDS):
    - Set `POSTGRES_INTERNAL=false` in `.env.docker`.
    - Configure `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`.
    - (Optional) Set `AUTO_CREATE_SCHEMA=true` if you want ThothAI to create the schema automatically.

## 2. Deployment

You can start the system using our helper scripts, the CLI, or manual commands.

### Option A: Helper Script (Recommended)

We provide a robust script that handles setup, network creation, and cleanup automatically. By default, it operates in **Compose mode**.

```bash
./docker-up.sh
```

To stop:
```bash
./docker-down.sh
```

### Option B: ThothAI CLI

If you have initialized the project with `thothai init`, you can use the CLI:

```bash
uv run thothai up
uv run thothai down
```

### Option C: Manual Docker Commands

If you prefer standard Docker tools:

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## 3. Accessing the Application

Once started (give it a minute to initialize), access the services:

- **Main Interface**: [http://localhost:8040](http://localhost:8040) (Served via Nginx Proxy)
- **Frontend Direct**: [http://localhost:3040](http://localhost:3040)
- **Backend Admin**: [http://localhost:8040/admin](http://localhost:8040/admin)

## 4. Volume Persistence & Data

Docker Compose uses named volumes to persist data even when containers are stopped.

- **`thoth-backend-db`**: Stores the SQLite database (if used) or persistent DB data.
- **`qdrant-data`**: Stores vector embeddings.
- **`thoth-data-exchange`**: A shared volume for exchanging files between services.

### Resetting Data
To completely wipe all data and start fresh (useful for testing):

```bash
docker compose down -v
```
*The `-v` flag removes the named volumes.*

## 5. Troubleshooting

### "Bind for 0.0.0.0:8040 failed: port is already allocated"
This means another service (possibly a local instance of ThothAI) is using the port.
**Fix**: Stop other instances or change `WEB_PORT` in `.env.docker`.

### "Connection refused" between containers
Ensure all services are running:
```bash
docker compose ps
```
If a service has `Exited`, check its logs:
```bash
docker compose logs backend
```
