ThothAI – Engineering Guide for Future Work

Overview
- Purpose: Unified Text-to-SQL platform with Django backend, Next.js frontend, and a FastAPI SQL Generator powered by PydanticAI agents.
- Core flow: User question → context retrieval (vector DB) → multi-agent SQL generation → validation → execution → optional explanation → results + CSV export.

Run Modes
- Docker (recommended): All services via `docker-compose` behind Nginx.
- Local dev: Run Django, SQL Generator, Qdrant (Docker), and Next.js directly using `./start-all.sh`.

Key Paths
- Root: `README.md:1`, `docker-compose.yml:1`, `start-all.sh:1`, `install.sh:1`, `config.yml.local:1`.
- Backend (Django): `backend/manage.py:1`, `backend/Thoth/settings.py:1`, `backend/thoth_core:1`, `backend/thoth_ai_backend:1`.
- Frontend (Next.js): `frontend/app:1`, `frontend/components:1`, `frontend/next.config.js:1`.
- SQL Generator (FastAPI + agents): `frontend/sql_generator/main.py:1`, `frontend/sql_generator/agents/core/agent_manager.py:1`, `frontend/sql_generator/agents/core/agent_initializer.py:1`, `frontend/sql_generator/agents/core/agent_ai_model_factory.py:1`.
- Dockerfiles: `docker/backend.Dockerfile:1`, `docker/sql-generator.Dockerfile:1`, `docker/frontend.Dockerfile:1`, `docker/proxy.Dockerfile:1`.
- Config templates: `.env.local.template:1`, `.env.docker.template:1`.
- Data/volumes bind mounts: `data_exchange:1`, `qdrant_storage:1`.

Services and Ports
- Backend (Django): API + Admin.
  - Docker: internal 8000, external via Nginx 8040.
  - Local dev: 8200 (from `.env.local`).
- Frontend (Next.js): Web app.
  - Docker: 3040 → container 3000.
  - Local dev: 3200.
- SQL Generator (FastAPI + PydanticAI): 8020 (Docker) / 8180 (local).
- Qdrant (vector DB): 6333 (Docker) / 6334 (local).
- Nginx proxy (Docker only): 8040 exposes backend + proxies frontend and SQL Generator.

Install and Start
- Docker install (preferred):
  1) Copy and edit `config.yml.local:1` (API keys, embedding, ports).
  2) Run installer: `./install.sh` (builds images, creates volumes/network, generates `.env.docker`, seeds data if first install).
  3) Access: Frontend http://localhost:3040, Admin http://localhost:8040/admin, API http://localhost:8040/api.
- Local dev quickstart:
  1) Copy `.env.local.template:1` → `.env.local`, set API keys and `DB_ROOT_PATH`.
  2) Run `./start-all.sh:1` (starts Django on 8200, SQL Generator on 8180 via uv, Qdrant via Docker, Next.js on 3200).
  3) URLs: Frontend http://localhost:3200, Backend http://localhost:8200, SQL Gen http://localhost:8180, Qdrant http://localhost:6334.

Configuration System
- Two parallel config flows (documented in `README.md:1`):
  - Docker: `config.yml.local` → `scripts/installer.py:1` → `.env.docker` + merged `pyproject.toml.local` → `docker-compose.yml:1` env.
  - Local dev: `config.yml.local` → `scripts/generate_env_local.py:1` → `.env.local`
    - Database extras resolved via `scripts/update_local_db_dependencies.py:1` producing `backend/pyproject.toml.local` and `frontend/sql_generator/pyproject.toml.local`
    - `start-all.sh:1` runs `uv lock --refresh && uv sync` inside both directories when dependencies change
    - `.env.local` exported with `PORT` filtered out, same as before
- Required env:
  - LLMs: at least one of `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` (plus optional Mistral, DeepSeek, OpenRouter, Ollama, LM Studio).
  - Embeddings: `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`.
  - DB root path for dev tests: `DB_ROOT_PATH` (absolute path recommended for test datasets).
  - Optional monitoring: `LOGFIRE_TOKEN`.
- Secrets: `.env.*` and `config.yml.local` are not committed; installer writes `.env.docker`. Do not edit `.env.docker` manually.

Docker Orchestration
- Compose file: `docker-compose.yml:1` defines 5 services: `backend`, `frontend`, `sql-generator`, `proxy`, `thoth-qdrant`.
- External volumes and network created by installer:
  - Volumes: `thoth-backend-static`, `thoth-backend-media`, `thoth-frontend-cache`, `thoth-qdrant-data`, `thoth-secrets`, `thoth-backend-db`, `thoth-logs`, `thoth-shared-data`.
  - Network: `thoth-network`.
- Bind mounts (host ↔ container): `./data_exchange:/app/data_exchange` (runtime I/O), project secrets volume at `/secrets`.

Data and Paths
- `setup_csv:1`: initial configuration data loaded by backend during first boot.
- `data_exchange:1`: import/export folder for CSVs, docs, backups shared with containers.
- `qdrant_storage:1`: local persistence for the standalone Qdrant container in local dev.
- `backend/logs:1`, `frontend/sql_generator/logs:1`: local logs for dev mode.

Backend (Django)
- Entry: `backend/manage.py:1`, settings `backend/Thoth/settings.py:1`.
- Apps:
  - `backend/thoth_core:1`: core models (Users, SQL DBs, Vector DBs, Workspaces, AI models, Agents).
  - `backend/thoth_ai_backend:1`: workflows (preprocessing, admin views, vector DB ops, evidence, documents).
- Admin: Nginx proxies `/admin` in Docker; direct `/admin` on local port.
- Dependencies: `backend/pyproject.toml:1` (uv), extras enable MariaDB/SQL Server: `uv sync --extra mariadb|sqlserver`.
- Useful scripts: `backend/scripts:1` (cron, tests), `backend/setup-docker.sh:1` (helper), `backend/create_superuser.py:1`.

Frontend (Next.js)
- App: `frontend/app:1` with modern Next.js 14 routing; Tailwind configured via `frontend/tailwind.config.js:1`.
- Built for Docker with multi-stage `docker/frontend.Dockerfile:1` (Node 20-alpine).
- Local dev: `npm run dev` started by `start-all.sh:1` on `FRONTEND_PORT`.

SQL Generator Service (FastAPI + PydanticAI)
- Entrypoints: `frontend/sql_generator/main.py:1` (FastAPI server), `frontend/sql_generator/run_server.py:1`.
- Agents architecture:
  - Manager: `agents/core/agent_manager.py:1` creates and wires agents, validators, and pools.
  - Factory: `agents/core/agent_initializer.py:1` builds specific agents and attaches templates + types.
  - Model provider factory: `agents/core/agent_ai_model_factory.py:1` resolves providers and keys, supports OpenAI, Anthropic, Gemini, Mistral, DeepSeek, OpenRouter, Ollama, LM Studio, with fallback chaining via `FallbackModel`.
  - Dynamic pools: `model/agent_pool_config.py:1` enables SQL/test agents by level (basic/advanced/expert) loaded from backend; manager supports legacy (fixed 3) and dynamic pools.
  - Validators: `agents/validators/*:1` attach output validators (e.g., SQL validation) where enabled.
- Agent types (typical):
  - Question validator and translator.
  - Keyword extraction.
  - SQL generation: basic, advanced, expert (single agents; manager selects via template metadata).
  - Test generation x3 + evaluator; optional TestReducer.
  - SQL explanation agent (returns string explanation for UI).
- Prompting:
  - System prompts loaded via `helpers/template_preparation.py:1` from `system_templates/*`.
  - SQL generation differentiates via user prompt templates; system prompt is unified (`system_template_generate_sql.txt`).
- Environment resolution for models:
  - If `DOCKER_CONTAINER=true` then `.env.docker` is loaded; else `.env.local`.
  - Providers read API keys from agent config first, then env variables.
  - Ollama/LM Studio expect OpenAI-compatible endpoints (ensure `/v1` suffix for base URL).

Service Communication
- Docker: `frontend` and `sql-generator` talk to `backend` through `proxy` or direct service hosts; envs set in compose (`DJANGO_SERVER=http://proxy:80`, `SQL_GENERATOR_URL=http://sql-generator:8020`).
- Local: Next.js uses `NEXT_PUBLIC_*` envs; SQL Generator reads `DJANGO_SERVER` and vector DB host/port from `.env.local`.

Logging
- Docker: use `docker compose logs -f [service]`.
- Local: backend logs to `backend/logs:1`; SQL Generator logs to `frontend/sql_generator/logs:1`.

Common Developer Tasks
- Docker fresh setup: `./install.sh` (options: `--clean-cache`, `--prune-all [--dry-run|--force]`).
- Start locally: `./start-all.sh`.
- Stop local stack: Ctrl+C in the script prompt (it traps and cleans up); optionally stop `qdrant-thoth` container.
- Backend migrations (local): `cd backend && uv run python manage.py makemigrations && uv run python manage.py migrate`.
- Create superuser (local): `cd backend && uv run python manage.py createsuperuser`.
- Frontend local dev: `cd frontend && npm install && PORT=3200 npm run dev`.
- SQL Generator direct run: `cd frontend/sql_generator && uv run python main.py`.
- Docker logs: `docker compose logs -f`.

Special Libraries
- thoth-dbmanager: sources avaliable at /Users/Thoth/thoth-sqldb2
- thoth-qdrant: sources avaliable at /Users/Thoth/thoth-vdb3

Testing
- Backend: `backend/tests:1` with pytest; run via `cd backend && uv run pytest` or `backend/scripts/run-tests-local.sh:1`.
- SQL Generator: unit tests live near agents/validators; run with uv in `frontend/sql_generator` environment.

Troubleshooting
- Ports in use: adjust in `config.yml.local:1` (Docker) or `.env.local:1` (local), or free with `lsof` as `start-all.sh:1` does.
- API key errors: ensure at least one LLM and the embedding provider are configured; for OpenRouter/DeepSeek set `*_API_BASE` if needed.
- Qdrant connectivity: Docker 6333, local 6334; ensure container `qdrant-thoth` is running in local dev.
- Missing uv: install via `curl -LsSf https://astral.sh/uv/install.sh | sh` (required for Python deps).
- `.env` precedence for agents: `DOCKER_CONTAINER` determines which `.env` is parsed; mismatched keys lead to model factory errors.

Security Notes
- Never commit real API keys. The repo includes templates; use local copies.
- Secrets volume `thoth-secrets` is mounted at `/secrets` in containers; file permissions are restricted.
- Consider enabling HTTPS termination in production; update Nginx config under `docker/nginx.conf:1` or proxy image template.

Design Decisions Worth Knowing
- PydanticAI agents use lightweight `deps_type` models (SqlGenerationDeps, EvaluatorDeps, etc.) instead of a heavy shared state; SQL execution happens in validators, not as agent tools.
- SQL generation uses unified system prompt; diversity comes from user prompt templates and distinct agent “levels”.
- `FallbackModel` stacks the specific agent model with the workspace default model to increase robustness.
- Dynamic agent pools (from Django) are supported, but legacy single-agent-per-level path remains the default.

Cheat Sheet (one-liners)
- Docker install: `./install.sh` → open http://localhost:3040 and http://localhost:8040/admin
- Local start: `./start-all.sh`
- Backend shell: `cd backend && uv run python manage.py shell`
- SQL Gen run: `cd frontend/sql_generator && uv run python main.py`
- Frontend dev: `cd frontend && npm run dev`
- Watch logs: `docker compose logs -f proxy backend sql-generator frontend`

Next Steps When Coming Back
- If Docker: update repo then re-run `./install.sh` to rebuild with latest templates/env.
- If local: verify `uv` installed and `.env.local` valid; run `./start-all.sh`.
- For agent tweaks: start from `agent_manager.py:1` and `agent_initializer.py:1`; provider setup in `agent_ai_model_factory.py:1`.
