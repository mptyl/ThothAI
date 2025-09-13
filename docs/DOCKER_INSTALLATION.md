# ThothAI – Docker Installation with Preloaded Demo Data

This guide explains the Docker installation procedure started by the `install.sh` script. On Windows, use PowerShell with `install.ps1` and run shell (`.sh`) scripts inside WSL. At the end of the installation you will have a complete stack (backend, frontend, SQL Generator, Nginx proxy, Qdrant) running, with the demo database `california_schools` preloaded and a `demo` user ready to use.

Note for Windows users:
- We assume Docker Desktop with WSL 2 backend enabled.
- Prefer the dedicated Windows guide: `docs/WINDOWS_INSTALLATION.md` for OS-specific details and troubleshooting.

—

## 1) Prerequisites

Make sure you have installed and working:

- Docker and Docker Compose (v2, i.e. `docker compose`)
- Python 3.9+

The `install.sh` script (Linux/macOS) and `install.ps1` (Windows) automatically check for prerequisites and stop if something is missing.

—

## 2) Initial configuration (`config.yml.local`)

Before running the installer you must manually create `config.yml.local` from the template. You can copy `config.yml` to `config.yml.local` and then fill it in. The `install.sh` script requires that `config.yml.local` exists; otherwise it stops execution. Configuration validation is performed via `scripts/validate_config.py`, which checks:

- AI providers in `ai_providers`. At least one provider must be enabled and have an API key.
- Embedding settings (`embedding.provider`, `embedding.model`, and matching API key or fallback to the provider). There must be at least one enabled embedding provider.
- Database configuration (`databases`, with SQLite always enabled).
- `admin` section (at least `username`; email is optional). Also define `demo` with its password.
- `monitoring` section (if enabled, requires `logfire_token`).
- `ports` section with non-duplicated ports in the 1024–65535 range.

Reference file: `scripts/validate_config.py`.

Note for local development: the local startup script (`start-all.sh`) does not read `config.yml.local`; it loads and validates `.env.local`. To change the backend AI provider/model in local mode, edit `.env.local` (keys `BACKEND_AI_PROVIDER` and `BACKEND_AI_MODEL`).

—

## 3) Running the installer

The main flow is implemented in `scripts/installer.py` and invoked by `install.sh` (Linux/macOS) or `install.ps1` (Windows). Key phases:

1. Load and validate configuration: `ThothInstaller.load_config()` + basic validation.
2. Admin password: asked or read from config; the hash is saved to `.admin_password.hash`.
3. Local dependencies: creates `backend/pyproject.toml.local` with the required DB extras and `frontend/sql_generator/pyproject.toml.local`.
4. Merge `pyproject.toml`: produces `pyproject.toml.merged` in `backend/` and `frontend/sql_generator/` by merging base + local.
5. Generate `.env.docker`: writes all necessary variables (AI providers, embedding, monitoring, admin, port mapping, etc.). File: `.env.docker` (auto-generated, do not edit manually).
6. Docker network: creates the network if missing (default: `thoth-network`).
7. Docker volumes: creates persistent volumes (`thoth-secrets`, `thoth-backend-static`, `thoth-backend-media`, `thoth-frontend-cache`, `thoth-qdrant-data`, `thoth-shared-data`).
8. Django secrets: generates two files in the `thoth-secrets` volume if missing: `django_secret_key` and `django_api_key`.
9. Build & up services: `docker compose build` and then `docker compose up -d` on the compose file (default: `docker-compose.yml`).
10. Wait for backend: attempts a connection until available.
11. Initial setup: primarily executed during backend startup (`backend/scripts/start.sh`). If the installation is “greenfield” and LLM API keys are present, the installer may also invoke demo helpers (`generate_db_scope_demo`, `generate_db_documentation_demo`, `scan_gdpr_demo`).

Reference file: `scripts/installer.py`.

—

## 4) Docker services and network

The `docker-compose.yml` file defines the main services:

- `backend` (Django + Gunicorn). Volumes: static, media, SQLite DB, `thoth-secrets`, `thoth-shared-data`. Starts via `backend/entrypoint-backend.sh` → `/start.sh`.
- `frontend` (Next.js). Reads `DJANGO_API_KEY` from the secrets volume in `frontend/entrypoint-frontend.sh` (copied as the entrypoint in the image).
- `sql-generator` (auxiliary service). Reads `DJANGO_API_KEY` in `frontend/sql_generator/entrypoint-sql-generator.sh`.
- `proxy` (Nginx). Routes requests to frontend, backend, and sql-generator. Built with `docker/proxy.Dockerfile` (config in `backend/proxy/`), not `docker/nginx.conf`.
- `thoth-qdrant` (Vector DB). Persistence in `thoth-qdrant-data` volume.

All services are attached to the dedicated Docker network (default `thoth-network`).

Reference file: `docker-compose.yml`.

—

## 5) Secrets management

- Secrets volume: `thoth-secrets` mounted as `/secrets` inside containers.
- During installation, `scripts/installer.py` checks and if needed creates:
  - `/secrets/django_secret_key`
  - `/secrets/django_api_key`
- The backend loads them in `backend/entrypoint-backend.sh` and `backend/scripts/start.sh`.
- The frontend and `sql-generator` read `DJANGO_API_KEY` respectively in:
  - `frontend/entrypoint-frontend.sh`
  - `frontend/sql_generator/entrypoint-sql-generator.sh`

—

## 6) Preloading `california_schools` demo data

The CSVs for the demo workspace are in `setup_csv/docker/`:

- `california_schools_tables.csv`
- `california_schools_columns.csv`
- `california_schools_relationships.csv`
- `selected_dbs.csv`, `vectordb.csv` (additional configs)

Loading and configuration happen during backend startup in `backend/scripts/start.sh` when the system detects a “greenfield” state (no existing `Workspace`):

1. Initialize SQLite DB, run `makemigrations` and `migrate`.
2. Full cleanup for a clean installation (Workspaces, SQL structures, AI configurations, VectorDB, groups).
3. Load default configurations: `manage.py load_defaults --source docker` (includes groups, models, settings, and possible default users).
4. Set/update `admin` and `demo` user passwords from `config.yml.local` if present.
5. Link the demo workspace (`id=1`) to the `demo` user and set it as default.
6. AI-assisted operations, if LLM API keys are present: `manage.py generate_scope --workspace 1`, `manage.py generate_documentation --workspace 1`, `manage.py scan_gdpr --workspace 1`.
7. Demo preprocessing: load evidence and “Gold SQL” (Q/A pairs) and start preprocessing tasks towards the Vector DB.

Note: if the installer detects a “greenfield” installation with configured API keys, it may also run additional demo helpers (`generate_db_scope_demo`, `generate_db_documentation_demo`, `scan_gdpr_demo`).

These actions allow the `demo` user to immediately use the `california_schools` database without manual configuration.

Reference files: `backend/scripts/start.sh`, CSVs under `setup_csv/docker/`.

—

## 7) Ports and access URLs

Ports are defined in `config.yml.local` (and propagated into `.env.docker`) and mapped in `docker-compose.yml`. Typical defaults:

- Frontend: `http://localhost:<FRONTEND_PORT>` (3040)
- Backend API via Nginx proxy: `http://localhost:<WEB_PORT>` (8040) — the `/api` endpoint and admin are exposed by the proxy.
- SQL Generator: `http://localhost:<SQL_GENERATOR_PORT>` (8020)
- Nginx (proxy): `http://localhost:<WEB_PORT>` (8040)

Useful paths:

- Main application via Nginx: `http://localhost:<WEB_PORT>`
- Django admin (via proxy): `http://localhost:<WEB_PORT>/admin`

—

## 8) Access credentials

Set from `config.yml.local` during the first run (greenfield):

- Admin superuser: username/email/password as specified in `admin`.
- Demo superuser: username/email/password as specified in `demo`.

On subsequent starts, if workspaces already exist, the script avoids a full setup but verifies that admin/demo users exist and creates them if missing.

—

## 9) Start, logs, and maintenance

Main commands:

- Build/Start (Linux/macOS): `./install.sh` (runs the entire pipeline: build + up)
- Build/Start (Windows): `./install.ps1`
- View logs: `docker compose logs -f`
- Restart services: `docker compose restart`
- Stop stack: `docker compose down`
- Update (Linux/macOS): `git pull && ./install.sh`
- Update (Windows): `git pull && ./install.ps1`

—

## 10) Frequently Asked Questions (FAQ)

- No AI provider configured: installation still works; AI analyses, automatic documentation, and GDPR scan will be skipped. Add an API key in `config.yml.local` and rerun `./install.sh`.
- Where is persistent data stored?
  - Secrets: `thoth-secrets` volume
  - Backend media/static: `thoth-backend-media`, `thoth-backend-static`
  - Qdrant: `thoth-qdrant-data`
  - Shared data: `thoth-shared-data`
  - Backend SQLite DB: file in `/app/backend_db/` inside the container, volume-mapped
- How to change ports? Edit the `ports` section in `config.yml.local` and rerun `./install.sh`.

—

## 11) Code references

- Installer pipeline: `scripts/installer.py`
- Config/API key validation: `scripts/validate_config.py`
- Compose and services: `docker-compose.yml`
- Backend Dockerfile: `docker/backend.Dockerfile`
- Frontend Dockerfile: `docker/frontend.Dockerfile`
- Backend entrypoint: `backend/entrypoint-backend.sh`
- Backend startup: `backend/scripts/start.sh`
- Frontend entrypoint: `frontend/entrypoint-frontend.sh`
- SQL Generator entrypoint: `frontend/sql_generator/entrypoint-sql-generator.sh`
- Proxy: build `docker/proxy.Dockerfile`, configurations in `backend/proxy/`
- Demo CSVs: `setup_csv/docker/`

—

With this procedure, the ThothAI Docker environment is installed and started in a repeatable and safe way, with demo data ready to use and a demo user already configured. To enable AI-assisted features, remember to set at least one valid API key in `config.yml.local` and repeat the installation (`./install.sh` on Linux/macOS, `./install.ps1` on Windows).
