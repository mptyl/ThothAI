# Docker Compose From Docker Hub

This is the only supported public installation path for ThothAI.

It uses:

- `docker-compose-hub.yml` to pull prebuilt images from Docker Hub
- `.env.docker` for runtime environment variables
- `config.yml.local` for provider, embedding, admin, and runtime configuration

Local source installs, hybrid local development, and Docker Swarm are intentionally excluded from the published documentation. Those materials remain in the repository archive under `legacy-docs/`.

## Prerequisites

- Docker Engine or Docker Desktop with Compose v2
- Access to Docker Hub
- At least one LLM API key
- An embedding provider API key

## 1. Clone the Repository

```bash
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI
```

## 2. Prepare the Required Files

```bash
cp .env.compose.template .env.docker
cp config.yml config.yml.local
```

The public install flow assumes `BUILD_MODE=hub` in `.env.docker`, which is already the default in `.env.compose.template`.

## 3. Review the Compose File

Start from `docker-compose-hub.yml`.

This file:

- pulls `tylconsulting/thoth-*` images instead of building locally
- mounts `config.yml.local` into the backend container
- uses `.env.docker` for ports, provider keys, logging, and database settings
- expects the default Docker network and named volumes declared in the file

Run it with:

```bash
docker compose -f docker-compose-hub.yml up -d
```

## 4. Stop the Stack

```bash
docker compose -f docker-compose-hub.yml down
```

Volumes are preserved by default. Remove them only if you explicitly want a clean reinstall.

## Supported Runtime Shape

The published installation path assumes these services:

- `backend`
- `frontend`
- `sql-generator`
- `proxy`
- `mermaid-service`
- `thoth-qdrant`

The internal PostgreSQL service is available only in `docker-compose.yml`. The Docker Hub deployment path is documented around the prebuilt images and the mounted runtime configuration.
