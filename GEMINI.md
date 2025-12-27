# ThothAI - Gemini Context

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
- Backend: [thoth_core](file:///Users/mp/ThothAI/backend/thoth_core), [thoth_ai_backend](file:///Users/mp/ThothAI/backend/thoth_ai_backend).
- Frontend: [app](file:///Users/mp/ThothAI/frontend/app), [agents](file:///Users/mp/ThothAI/frontend/sql_generator/agents).
- Docs: `docs/thothai_install/`, `data_exchange/`.

## Services and Ports
- **Backend (Django)**: 8200 (Local) / 8000 (Docker internal) / 8040 (Docker external)
- **Frontend (Next.js)**: 3200 (Local) / 3000 (Docker internal) / 3040 (Docker external)
- **SQL Generator**: 8180 (Local) / 8020 (Docker internal)
- **Qdrant**: 6334 (Local) / 6333 (Docker internal)
- **Mermaid Service**: Self-hosted diagram generation (Docker)
- **Docker Swarm Ports**: Configurable range 7000-7020 (default: Proxy=7010, Frontend=7001, Backend=7002, SQL-Gen=7003, Mermaid=7004, Qdrant=7005)

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
- **Manager**: `agent_manager.py` orchestrates agents.
- **Factory**: `agent_initializer.py` builds specific agents.
- **Agent Types**:
    - `QuestionValidator`: Checks validity and scope.
    - `QuestionTranslator`: Translates to DB language.
    - `KeywordExtraction`: Extracts entities.
    - `SQL Generators` (BASIC, ADVANCED, EXPERT): Generate SQL.
    - `Evaluator`: Validates SQL candidates.
    - `Test Generators` & `TestReducer`: Create and optimize validation tests.
    - `SqlExplainer`: Explains queries in natural language.

## Key Features & Notes
- **Hybrid Data Exchange**: Sync data between environments using `data-exchange-cli.py`.
- **Database Support**: PostgreSQL, MySQL, SQLite, MariaDB, SQL Server, **Informix** (via SSH Tunnel).
- **SSH Tunnels**: Supported for secure database connections.
- **Line Endings**: Enforced LF via `.gitattributes`.
- **Test Data**: `DB_ROOT_PATH` must point to BIRD test databases.
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
