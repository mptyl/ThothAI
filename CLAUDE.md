# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Practices

- Always put the copyright info as file header in the coding file. Not in config, doc or other files:
  ```
  # Copyright (c) 2025 Marco Pancotti
  # This file is part of ThothAI and is released under the Apache 2.0.
  # See the LICENSE.md file in the project root for full license information.
  ```
- Always put an Apache 2.0 LICENSE.md in the directory when you init the project and you don't find it
- Use English for comment and documentation if not specified otherwise

## Project Overview
**ThothAI** is a unified Text-to-SQL platform designed to generate SQL queries from natural language using advanced AI agents.
- **Core flow**: User question → context retrieval (vector DB) → multi-agent SQL generation → validation → execution → optional explanation → results + CSV export.

## Technology Stack
- **Backend**: Django REST Framework (Python)
- **Frontend**: Next.js (React/TypeScript)
- **SQL Generator**: FastAPI with PydanticAI (Python)
- **Database**: PostgreSQL (Application DB), Qdrant (Vector DB)
- **Infrastructure**: Docker Compose, Docker Swarm, Nginx
- **Package Management**: `uv` (Python), `npm` (Node.js)

## Key Directories
- Root: [README.md](file:///Users/mp/ThothAI/README.md), [docker-compose.yml](file:///Users/mp/ThothAI/docker-compose.yml), [start-all.sh](file:///Users/mp/ThothAI/start-all.sh), [install.sh](file:///Users/mp/ThothAI/install.sh), [config.yml.local](file:///Users/mp/ThothAI/config.yml.local).
- Backend (Django): [manage.py](file:///Users/mp/ThothAI/backend/manage.py), [settings.py](file:///Users/mp/ThothAI/backend/Thoth/settings.py), [thoth_core](file:///Users/mp/ThothAI/backend/thoth_core), [thoth_ai_backend](file:///Users/mp/ThothAI/backend/thoth_ai_backend).
- Frontend (Next.js): [app](file:///Users/mp/ThothAI/frontend/app), [components](file:///Users/mp/ThothAI/frontend/components), [next.config.js](file:///Users/mp/ThothAI/frontend/next.config.js).
- SQL Generator (FastAPI + agents): [main.py](file:///Users/mp/ThothAI/frontend/sql_generator/main.py), [agent_manager.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_manager.py), [agent_initializer.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_initializer.py), [agent_ai_model_factory.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_ai_model_factory.py).
- Dockerfiles: `docker/backend.Dockerfile`, `docker/sql-generator.Dockerfile`, `docker/frontend.Dockerfile`, `docker/proxy.Dockerfile`.
- Config templates: `.env.local.template`, `.env.docker.template`.
- Data/volumes bind mounts: `data_exchange`, `qdrant_storage`.

## Services and Ports
- **Backend (Django)**: 8200 (Local) / 8000 (Docker internal) / 8040 (Docker external)
- **Frontend (Next.js)**: 3200 (Local) / 3000 (Docker internal) / 3040 (Docker external)
- **SQL Generator**: 8180 (Local) / 8020 (Docker internal)
- **Qdrant**: 6334 (Local) / 6333 (Docker internal)
- **Mermaid Service**: Self-hosted diagram generation (Docker)
- **Docker Swarm Ports**: Configurable range 7400-7420

## Development Workflow

### Configuration
- **Source of Truth**: `config.yml.local` (Gitignored).
- **Docker Config**: `.env.docker` (Generated from `config.yml.local`).
- **Local Config**: `.env.local` (Generated from `config.yml.local`).
- **Required Env**:
    - LLMs: `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `ANTHROPIC_API_KEY`.
    - Embeddings: `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY`.

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
uv run python manage.py createsuperuser
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

#### Code Quality
```bash
# Backend (uses ruff)
cd backend
uv run ruff check .
uv run ruff format .

# Frontend
cd frontend
npm run lint
npm run format
```

## Agents Architecture (PydanticAI)
Located in `frontend/sql_generator/agents/`:
- **Manager**: [agent_manager.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_manager.py) orchestrates agents.
- **Factory**: [agent_initializer.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_initializer.py) builds specific agents.
- **Model Provider Factory**: [agent_ai_model_factory.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/core/agent_ai_model_factory.py) resolves providers with `FallbackModel`.
- **Agent Types**:
  - `QuestionValidator`: Checks if question is valid and in-scope.
  - `QuestionTranslator`: Translates question to DB language.
  - `KeywordExtraction`: Extracts entities.
  - `SQL Generators` (BASIC/ADVANCED/EXPERT): Single agents for specific levels.
  - `Test Generators`: Generate validation test cases.
  - `Evaluator`: Evaluates SQL candidates against test units.
  - `SqlEvaluator`: "Belt and Suspenders" logic for borderline SQL candidates.
  - `TestReducer`: Semantic deduplication of test cases.
  - `SqlExplainer`: Generates human-readable explanations.
- **Logic Details**:
  - Pure Python Validators in [sql_validators.py](file:///Users/mp/ThothAI/frontend/sql_generator/agents/validators/sql_validators.py).
  - Lightweight State using `deps_type` models.

## Key Features & Notes
- **Hybrid Data Exchange**: Sync data between environments using `data-exchange-cli.py`.
- **Database Support**: PostgreSQL, MySQL, SQLite, MariaDB, SQL Server, **Informix** (via SSH Tunnel).
- **SSH Tunnels**: Supported for secure database connections.
- **Line Endings**: Enforced LF via `.gitattributes`.
- **Test Data**: `DB_ROOT_PATH` must point to BIRD test databases.
- **Direnv**: Supported via `.envrc`.

## API Endpoints
- `/health`: Service status.
- `/generate-sql`: Main streaming endpoint via orchestration.
- `/explain-sql`: Generates human-readable SQL explanation.
- `/execute-query`: Executes SQL with pagination (Next.js AGGrid).
- `/save-sql-feedback`: Saves "Like" feedback and SQL examples to Qdrant.

## Logging and Monitoring
- Logfire: Integrated via `logfire.instrument_pydantic_ai()` for full telemetry.
- Dual Logger: Logic for both file logs and streaming THOTHLOG lines for the UI.

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