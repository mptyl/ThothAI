# ThothAI – Engineering Guide for Future Work

## Development Practices
- Always put the copyright info as file header in the coding file. Not in config, doc or other files:
  ```
  # Copyright (c) 2025 Marco Pancotti
  # This file is part of ThothAI and is released under the Apache 2.0.
  # See the LICENSE.md file in the project root for full license information.
  ```
- Always put an Apache 2.0 LICENSE.md in the directory when you init the project and you don't find it
- Use English for comment and documentation if not specified otherwise

## Overview
- Purpose: Unified Text-to-SQL platform with Django backend, Next.js frontend, and a FastAPI SQL Generator powered by PydanticAI agents.
- Core flow: User question → context retrieval (vector DB) → multi-agent SQL generation → validation → execution → optional explanation → results + CSV export.

## Key Paths
- Root: [README.md](file:///Users/mp/ThothAI/README.md), [docker-compose.yml](file:///Users/mp/ThothAI/docker-compose.yml), [start-all.sh](file:///Users/mp/ThothAI/start-all.sh), [install.sh](file:///Users/mp/ThothAI/install.sh), [config.yml.local](file:///Users/mp/ThothAI/config.yml.local).
- Backend (Django): [manage.py](file:///Users/mp/ThothAI/backend/manage.py), [settings.py](file:///Users/mp/ThothAI/backend/Thoth/settings.py), [thoth_core](file:///Users/mp/ThothAI/backend/thoth_core), [thoth_ai_backend](file:///Users/mp/ThothAI/backend/thoth_ai_backend).
- Frontend (Next.js): [app](file:///Users/mp/ThothAI/frontend/app), [components](file:///Users/mp/ThothAI/frontend/components), [next.config.js](file:///Users/mp/ThothAI/frontend/next.config.js).
- SQL Generator (FastAPI + agents): [main.py](file:///Users/mp/ThothAI/frontend/sql_generator/main.py), [agent_manager.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_manager.py), [agent_initializer.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_initializer.py), [agent_ai_model_factory.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_ai_model_factory.py).
- Dockerfiles: `docker/backend.Dockerfile`, `docker/sql-generator.Dockerfile`, `docker/frontend.Dockerfile`, `docker/proxy.Dockerfile`.
- Config templates: `.env.local.template`, `.env.docker.template`.
- Data/volumes bind mounts: `data_exchange`, `qdrant_storage`.

## Services and Ports
- Backend (Django): API + Admin.
  - Docker: internal 8000, external via Nginx 8040.
  - Local dev: 8200 (from `.env.local`).
- Frontend (Next.js): Web app.
  - Docker: 3040 → container 3000.
  - Local dev: 3200.
- SQL Generator (FastAPI + PydanticAI): 8020 (Docker) / 8180 (local).
- Qdrant (vector DB): 6333 (Docker) / 6334 (local).
- Nginx proxy (Docker only): 8040 exposes backend + proxies frontend and SQL Generator.
- Docker Swarm Ports: Configurable range 7400-7420.

## Development Workflow

### Configuration
- Two parallel config flows:
  - Docker: `config.yml.local` → `scripts/installer.py` → `.env.docker` + merged `pyproject.toml.local` → `docker-compose.yml` env.
  - Local dev: `config.yml.local` → `scripts/generate_env_local.py` → `.env.local`
- Required env:
  - LLMs: at least one of `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`.
  - Embeddings: `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`.

### Common Development Commands

#### Quick Start
```bash
# Interactive installer (recommended)
./install.sh                    # Linux/macOS
install.ps1                     # Windows

# Docker setup
docker-compose up --build       # Start all services
docker-compose down            # Stop all services

# Docker Swarm setup
./install-swarm.sh             # Install Swarm
./deploy-swarm.sh              # Deploy Stack

# Local development (with uv)
./start-all.sh                 # Start all services locally
```

#### Backend Development
```bash
cd backend
uv sync                        # Install dependencies
uv run python manage.py migrate
uv run python manage.py runserver 8200
uv run pytest                  # Run tests
```

#### Frontend Development
```bash
cd frontend
npm install
npm run dev                    # Port 3200 (local)
npm run build
npm test
```

#### SQL Generator Service
```bash
cd frontend/sql_generator
uv sync
uv run python main.py          # Port 8180 (local)
```

## Agents Architecture (PydanticAI)
Located in `frontend/sql_generator/agents/`:
- **Manager**: [agent_manager.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_manager.py) orchestrates agents.
- **Factory**: [agent_initializer.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_initializer.py) builds specific agents.
- **Model Provider Factory**: [agent_ai_model_factory.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_ai_model_factory.py) resolves providers with `FallbackModel`.
- **Agent Types**:
  - `QuestionValidator`: Checks validity.
  - `QuestionTranslator`: Translates to DB language.
  - `KeywordExtraction`: Extracts entities.
  - `SQL Generators` (BASIC/ADVANCED/EXPERT): Main generation logic.
  - `Test Generators`: Generate validation tests.
  - `Evaluator`: Validates candidates.
  - `TestReducer`: Optimizes test cases.
  - `SqlExplainer`: Natural language explanations.

## Key Features & Notes
- **Hybrid Data Exchange**: Sync data between environments using `data-exchange-cli.py`.
- **Database Support**: PostgreSQL, MySQL, SQLite, MariaDB, SQL Server, **Informix** (via SSH Tunnel).
- **SSH Tunnels**: Supported for secure database connections.
- **Direnv**: Supported via `.envrc`.

## CURL Testing

**ALWAYS TEST ON DOCKER UNLESS SPECIFICALLY REQUESTED OTHERWISE!**
This means that every time you want to test with curl you must first build the service you want to test.

### Local environment:
```bash
curl -X POST "http://localhost:8180/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 1,
    "question": "Show me students in grade 10",
    "username": "demo",
    "functionality_level": "BASIC",
    "flags": {"use_schema": true}
  }' 2>/dev/null | python -m json.tool
```

### Docker environment:
```bash
curl -X POST "http://localhost:8020/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 1,
    "question": "Show me students in grade 10",
    "username": "demo",
    "functionality_level": "BASIC",
    "flags": {"use_schema": true}
  }' 2>/dev/null | python -m json.tool
```

## Docker Deployment Notes
You must always be in the root directory to deploy on Docker. Local Docker services can only be activated after doing a general docker compose.
