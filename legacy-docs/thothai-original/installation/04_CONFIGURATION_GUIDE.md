# Configuration Guide

ThothAI configuration is centralized in simple environment files. This approach ensures secrets are never committed to git and deployments are reproducible.

## Files Overview

| File | Purpose | Environment | Git Status |
|------|---------|-------------|------------|
| **`.env.docker`** | Active Config (Copied from template) | Production / Docker Dev | `gitignored` |
| **`.env.local`** | Config for local native execution | Local Development | `gitignored` |
| **`swarm_config.env`** | Swarm Infrastructure Config (Ports, Stack) | Docker Swarm | `gitignored` |
| `.env.compose.template` | Template source for Local Docker Compose | - | Committed |
| `.env.swarm.template` | Template source for Swarm Production | - | Committed |
| `swarm_config.env.template` | Template source for `swarm_config.env` | - | Committed |

## Variable Reference

### Deployment & Build

| Variable | Description | Valid Values | Default |
|----------|-------------|--------------|---------|
| `DEPLOYMENT_MODE` | Orchestrator selection | `compose`, `swarm` | `compose` |
| `BUILD_MODE` | Image source strategy | `hub` (pull), `build` (compile) | `hub` |
| `THOTH_DATA_PATH` | NFS/Bind Mount base path (Swarm only) | Absolute path | `/mnt/nfs/thothai` |
| `DOCKER_REGISTRY` | Registry for images | User/Org name | `tylconsulting` |
| `IMAGE_VERSION` | Tag to deploy | `latest`, `v1.0.0` | `latest` |

### Infrastructure & Ports

These ports defined where services listen on the **host machine**. In Swarm mode, these variables are loaded from `swarm_config.env`.

| Variable | Service | Default Port (Compose) | Default Port (Swarm) |
|----------|---------|------------------------|-----------------------|
| `WEB_PORT` | Nginx Proxy (Main Entry) | `8040` | `7010` |
| `FRONTEND_PORT` | Next.js Frontend (Direct) | `3040` | `7001` |
| `BACKEND_PORT` | Django Admin/API (via Proxy) | `8040` | `7002` |
| `SQL_GENERATOR_PORT` | SQL Gen Agent API | `8020` | `7003` |
| `MERMAID_SERVICE_PORT`| Diagram Service | `8003` | `7004` |
| `QDRANT_PORT` | Vector DB | `6333` | `7005` |

> [!NOTE]
> The `docker-swarm-up.sh` script prioritizes settings from `swarm_config.env` to avoid conflicts with existing Docker Compose installations on the same manager node.

### Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_INTERNAL` | Use internal DB container? | `true` |
| `AUTO_CREATE_SCHEMA`| Auto-create schema on startup? | `false` |
| `DB_HOST` | External DB Host | - |
| `DB_PORT` | External DB Port | `5432` |
| `DB_SCHEMA` | Schema name | `thoth_db_swarm` |

> [!TIP]
> **External DB on Host (Local)**: If running Swarm on Mac/Windows and you need to connect to a DB on the host (e.g., local Supabase), use `host.docker.internal` as `DB_HOST`.

### AI Providers (Application Logic)

You must configure **at least one** LLM provider for the application to function.

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Key for OpenAI (GPT-4o, etc.) |
| `ANTHROPIC_API_KEY` | Key for Claude models |
| `GEMINI_API_KEY` | Key for Google Gemini models |
| `EMBEDDING_PROVIDER` | Provider for vector embeddings (`openai`, `azure`, etc.) |
| `EMBEDDING_API_KEY` | Key for embedding service (often same as OpenAI key) |

### Runtime & Application

| Variable | Description |
|----------|-------------|
| `DEBUG` | Enable Django/Next.js debug mode | `true`, `false` |
| `LOGFIRE_TOKEN` | Token for Pydantic Logfire observability |
| `DB_ROOT_PATH` | **Absolute path** to test databases folder | Docker: `/app/data` |
| `ENTRA_ENABLED` | Enable Microsoft IdP integration | `true`, `false` |

## Security Keys Generation
 
Certain variables like `SECRET_KEY` (for Django) and `DJANGO_API_KEY` (for communication between frontend and backend) are critical for system security. While these are auto-generated in Docker Compose, you must configure them manually for local or Swarm installations.
 
To simplify this process, a dedicated script is available in the project root:
 
```bash
./generate-keys.sh
```
 
**Why use it?**
- **Security**: Generates high-entropy random keys.
- **Ease of Use**: You don't need to know internal Python commands to generate valid secrets.
- **Standardization**: Ensures keys are in the correct format expected by ThothAI.
 
Copy the generated values and paste them into the respective variables in your `.env.local` or `.env.swarm` files.
 
## Best Practices

1.  **Never Commit Secrets**: Ensure your `.env.docker` and `.env.local` files are never added to git.
2.  **Use Templates**: Always start from the `.template` file to ensure you have all required keys.
3.  **Port Management**: If you change `WEB_PORT`, remember to update your browser URL.
4.  **Passwords**: Change default passwords (`admin`/`changeme123`) immediately in production.
