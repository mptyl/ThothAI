<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

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
- Root: [README.md](file:///Users/mp/ThothAI/README.md), [docker-compose.yml](file:///Users/mp/ThothAI/docker-compose.yml), [install.sh](file:///Users/mp/ThothAI/install.sh), [config.yml.local](file:///Users/mp/ThothAI/config.yml.local).
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
- **Source of Truth**: `config.yml.local` (Gitignored).
- **Docker Config**: `.env.docker` (Generated from `config.yml.local`).
- **Required Env**:
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

## Database Plugin Runtime Configuration
Docker images contain **all** database drivers for portability, but which databases are actually usable is controlled at **runtime** via configuration.

### Architecture: Wrapper Pattern (No External Library Changes Required)

This solution uses a **wrapper pattern** that filters the output of `thoth_dbmanager` without requiring any modifications to the external library:

```
┌─────────────────────────────────────────────────────────────────────┐
│              EXTERNAL LIBRARY (thoth_dbmanager) - UNCHANGED         │
│                                                                     │
│  get_available_databases() returns:                                 │
│    {'sqlite': True, 'postgresql': True, 'mysql': True, ...}        │
│    (based on which drivers are installed)                          │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              THOTHAI CODE - initialize_database_plugins()           │
│                                                                     │
│  1. Calls get_available_databases() from thoth_dbmanager           │
│  2. Reads ENABLED_DATABASES from environment                        │
│  3. Filters the dictionary: disabled databases → False              │
│  4. Returns the filtered dictionary                                 │
│                                                                     │
│  Result: {'sqlite': True, 'postgresql': True, 'mysql': FALSE, ...}  │
│           ↑ MySQL disabled by config, not missing dependencies      │
└─────────────────────────────────────────────────────────────────────┘
```

### How It Works

1. **`config.yml.local`** defines which databases are enabled:
   ```yaml
   databases:
     sqlite: true       # Always required, cannot be disabled
     postgresql: true   # Enable for PostgreSQL support
     mysql: false       # Disabled - will not be available
     mariadb: true
     sqlserver: true
     informix: true
   ```

2. **`installer.py`** generates `ENABLED_DATABASES` in `.env.docker`:
   ```
   ENABLED_DATABASES=sqlite,postgresql,mariadb,sqlserver,informix
   ```

3. **At runtime**, our `initialize_database_plugins()` function:
   - Calls `thoth_dbmanager.get_available_databases()` (unmodified external library)
   - Reads `ENABLED_DATABASES` from environment variables
   - Filters the result: databases not in the list are marked as `False`
   - SQLite is always enabled regardless of configuration

### Implementation Details

The filtering logic in `backend/thoth_core/utilities/utils.py` and `frontend/sql_generator/helpers/main_helpers/main_methods.py`:

```python
# Get available databases from external library (unchanged)
available_databases = get_available_databases()

# Apply our runtime filtering
enabled_databases_env = os.environ.get("ENABLED_DATABASES", "").strip()
if enabled_databases_env:
    enabled_set = {db.strip().lower() for db in enabled_databases_env.split(",") if db.strip()}
    enabled_set.add("sqlite")  # Always enabled
    
    for db_name, is_available in available_databases.items():
        if db_name.lower() not in enabled_set:
            available_databases[db_name] = False  # Disabled by config
```

### Benefits
- **No External Library Changes**: `thoth_dbmanager` remains untouched and can be updated independently
- **Image Portability**: Pull the same Docker image from Docker Hub for any environment
- **No Rebuild Required**: Change database support by editing `config.yml.local` and regenerating `.env.docker`
- **Security**: Only expose the database drivers you actually need
- **Backward Compatible**: If `ENABLED_DATABASES` is not set, all installed databases remain available

### Build Architecture

**Important**: Docker images are built with **ALL database drivers** installed, regardless of `config.yml.local` settings:

| Component | All Drivers Included |
|-----------|---------------------|
| `backend/pyproject.toml` | `thoth-dbmanager[postgresql,sqlite,mariadb,sqlserver,informix]` |
| `frontend/sql_generator/pyproject.toml` | `thoth-dbmanager[postgresql,sqlite,mariadb,sqlserver,informix]` |
| `docker/backend.Dockerfile` | `uv sync --frozen --extra mariadb --extra sqlserver --extra all-databases` |

This means:
- **Build time**: All drivers are installed in the image
- **Runtime**: Only drivers listed in `ENABLED_DATABASES` are activated
- **config.yml.local databases section**: Controls **runtime** availability, not build-time installation

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
