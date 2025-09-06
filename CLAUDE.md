# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ThothAI is an AI-powered natural language to SQL conversion platform that enables users to query databases using plain language. The system uses multiple AI agents powered by PydanticAI to convert questions into SQL queries, execute them, and provide results with explanations.

## Architecture

### Docker Services
- **backend**: Django REST API managing configuration, metadata, and AI workflow (internal port 8000)
- **frontend**: Next.js web interface (port 3040)
- **sql-generator**: FastAPI service for SQL generation using PydanticAI agents (port 8020)
- **thoth-qdrant**: Vector database storing metadata, hints, and query examples (port 6333)
- **proxy**: Nginx reverse proxy (external port 8040, internal port 80)

### Key Components
- **thoth_core**: Core Django models, admin interface, database management
- **thoth_ai_backend**: AI workflow implementation, API endpoints, async tasks
- **sql_generator**: PydanticAI agents for SQL generation, validation, and testing

## Common Development Commands

### Quick Start
```bash
# Interactive installer (recommended)
./install.sh                    # Linux/macOS
install.ps1                     # Windows

# Docker setup
docker-compose up --build       # Start all services
docker-compose down            # Stop all services

# Local development (with uv)
./start-all.sh                 # Start all services locally
```

### Backend Development
```bash
cd backend
uv sync                        # Install dependencies
uv run python manage.py migrate
uv run python manage.py runserver 8200
uv run python manage.py createsuperuser
uv run python manage.py test
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev                    # Port 3200 (local)
npm run build
npm test
```

### SQL Generator Service
```bash
cd frontend/sql_generator
uv sync
uv run python main.py          # Port 8180 (local)

# Test the API
curl -X POST "http://localhost:8180/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 4,
    "question": "How many schools are exclusively virtual?",
    "username": "marco",
    "functionality_level": "BASIC",
    "flags": {
      "use_schema": true,
      "use_examples": true,
      "use_lsh": true,
      "use_vector": true
    }
  }'
```

### Testing
```bash
# Backend tests with isolated containers
cd backend
./scripts/run-tests-local.sh quick      # Quick smoke tests
./scripts/run-tests-local.sh full       # Full test suite with coverage
./scripts/run-tests-local.sh views      # View tests only
./scripts/run-tests-local.sh security   # Security tests only

# Direct pytest commands
cd backend
uv run pytest tests/                    # All tests
uv run pytest tests/ -m unit            # Unit tests only
uv run pytest tests/ -m integration     # Integration tests
uv run pytest -v --tb=short            # Verbose with short traceback
uv run pytest tests/integration/test_core_views.py::TestCoreViews::test_api_login_view  # Single test

# Frontend tests
cd frontend
npm test
```

### Code Quality
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

## Configuration

### Environment Variables
- Copy config.yml to config.yml.local and configure:
  - AI provider API keys (OpenAI, Anthropic, Gemini, Mistral, DeepSeek, OpenRouter, Ollama, LM Studio)
  - Embedding service configuration (OpenAI, Mistral, or Cohere)
  - Database drivers to enable (PostgreSQL, MySQL, MariaDB, SQL Server)
  - Service ports
  - Admin credentials
  - Monitoring (Logfire token)

### Port Configuration (Local Development)
- Backend Django: 8200
- Frontend Next.js: 3200
- SQL Generator: 8180
- Qdrant: 6334

### Port Configuration (Docker)
- Backend: 8000 (internal, accessed via proxy at 8040)
- Frontend: 3040
- SQL Generator: 8020
- Qdrant: 6333
- Web Proxy: 8040 (external), 80 (internal)

## Database Architecture

### SQL Databases
- Managed through thoth-dbmanager library
- Supports: PostgreSQL, MySQL, SQLite, MariaDB, SQL Server
- Connection format: `postgresql://user:password@host:port/dbname`

### Vector Databases
- Primary: Qdrant (via thoth-qdrant library)
- Stores: evidence, question/SQL pairs, table descriptions, semantic documentation
- Collections automatically created matching SQL database names

## AI Agent System

The SQL Generator uses PydanticAI agents located in `frontend/sql_generator/agents/`:
- **test_generator_with_evaluator**: Main SQL generation agent
- **sql_selector_agent**: Selects best SQL from candidates
- **evaluator_supervisor_agent**: Validates and improves SQL queries
- **test_reducer_agent**: Optimizes test cases

## API Endpoints

### Core APIs
- `/api/login/`: Authentication
- `/api/workspaces/`: Workspace management
- `/api/run-workflow/`: Execute AI query workflow (Django)
- `/generate-sql`: Generate SQL from natural language (FastAPI)
- `/explain-sql`: Get SQL explanation
- `/paginate-query`: Execute paginated queries

## Development Workflow

1. **Setup**: Install uv, copy config files, configure API keys
2. **Dependencies**: Use `uv sync` for Python, `npm install` for Node.js
3. **Database**: Run migrations with `uv run python manage.py migrate`
4. **Services**: Start with `./start-all.sh` (local) or `docker-compose up` (Docker)
5. **Testing**: Run tests before commits using pytest/npm test
6. **Quality**: Use ruff for Python, eslint for JavaScript

## Important Notes

1. **License**: Apache 2.0 - All new files must include license header
2. **Package Manager**: Use `uv` for Python dependency management
3. **Testing**: Always test locally before Docker deployment
4. **API Keys**: Store in Docker secrets volume or environment files
5. **Async Tasks**: Background tasks handled by Django's async capabilities
6. **Security**: Token-based authentication required for API access
7. **Templates**: PydanticAI templates use `ctx.deps` in system prompts, `{variable}` in user prompts

## Project Structure

```
ThothAI/
├── backend/                  # Django backend
│   ├── thoth_core/          # Core models and admin
│   ├── thoth_ai_backend/    # AI workflow
│   └── pytest.ini           # Test configuration
├── frontend/                 # Next.js frontend
│   ├── sql_generator/       # SQL generation service
│   │   ├── agents/          # PydanticAI agents
│   │   └── main.py          # FastAPI application
│   └── pyproject.toml       # Frontend Python deps
├── docker/                   # Dockerfiles
├── scripts/                  # Utility scripts
├── docker-compose.yml        # Service orchestration
└── install.sh               # Interactive installer
```

## Key Architectural Decisions

### AI Agent Workflow
The SQL generation follows a multi-agent pattern:
1. **Question Analysis**: Natural language processing and intent detection
2. **Schema Retrieval**: LSH-based schema matching + vector similarity search
3. **SQL Generation**: Multiple candidate queries generated using PydanticAI agents
4. **Validation & Selection**: Evaluator agent validates syntax and selects best query
5. **Execution & Formatting**: Query execution with result pagination support

### Authentication & Security
- Token-based authentication using Django REST Framework
- API keys stored in Docker secrets volume (production) or environment files (development)
- All API endpoints require authentication except `/api/login/`
- CORS configuration for frontend-backend communication

### Database Connection Management
- Connection pooling through SQLAlchemy
- Multiple database support via thoth-dbmanager plugin system
- Automatic vector collection creation matching SQL database names
- Test isolation using separate PostgreSQL and Qdrant containers

## Troubleshooting

- **Port conflicts**: Check and update ports in config.yml.local
- **API keys**: Ensure at least one AI provider and embedding service configured
- **Docker network**: Run `docker network create thoth-network` if missing
- **Dependencies**: Use `uv sync` to resolve Python dependency issues
- **Qdrant**: Ensure port 6334 (local) or 6333 (Docker) is available
- **Test containers**: Use `docker ps` to check if test containers are running


## CURL test 
TESTA SEMPRE SU DOCKER SE NON DIVERSAMENTE RICCHIESTO!!
Il che significa che ogni volta che vuoi testare con un curl devi proma fare la build del servizio che devi testara

In local development environment:
```bash
curl -X POST "http://localhost:8180/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 1,
    "question": "Please list the lowest three eligible free rates for students aged 5-17 in continuation schools.",
    "username": "demo",
    "functionality_level": "BASIC",
    "flags": {
      "use_schema": true,
      "use_examples": true,
      "use_lsh": true,
      "use_vector": true
    }
  }' 2>/dev/null | python -m json.tool
```
In docker development environment:
```bash
curl -X POST "http://localhost:8020/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 1,
    "question": "Please list the lowest three eligible free rates for students aged 5-17 in continuation schools.",
    "username": "demo",
    "functionality_level": "BASIC",
    "flags": {
      "use_schema": true,
      "use_examples": true,
      "use_lsh": true,
      "use_vector": true
    }
  }' 2>/dev/null | python -m json.tool
```
