# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Thoth is a Django-based backend application that enables querying relational databases using natural language. It uses AI agents powered by PydanticAI to convert natural language questions into SQL queries, execute them, and provide results with explanations.

## Architecture

The project consists of four main Docker services:
- **thoth-be**: Django backend managing configuration, metadata, and AI workflow
- **thoth-db**: PostgreSQL database for test/example databases  
- **thoth-qdrant**: Vector database storing metadata, hints, and query examples
- **thoth-be-proxy**: Nginx proxy for production deployment

Key Django apps:
- **thoth_core**: Core models, admin interface, database management
- **thoth_ai_backend**: AI workflow implementation, API endpoints, async tasks

## Common Development Commands

### Running the Application
```bash
# Quick installation (interactive installer)
./install.sh  # Linux/macOS
install.bat   # Windows

# Docker setup and run
./setup-docker.sh
docker-compose up --build

# Development server (local with uv)
uv run python manage.py runserver
```

### Testing
```bash
# Run quick tests
./scripts/run-tests-local.sh quick

# Run full test suite with coverage
./scripts/run-tests-local.sh full

# Run specific test categories
./scripts/run-tests-local.sh views     # View tests only
./scripts/run-tests-local.sh security  # Security tests only

# Run tests with pytest directly
pytest tests/                           # All tests
pytest tests/integration/test_core_views.py  # Specific test file
pytest -m unit                          # Unit tests only
pytest -v --tb=short                    # Verbose with short traceback
```

### Database Management
```bash
# Django migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Shell access
uv run python manage.py shell
```

### Code Quality
```bash
# The project uses ruff for linting and formatting
# Configuration is in pyproject.toml
uv run ruff check .
uv run ruff format .

# Run with uv (recommended for this project)
uv run pytest tests/
```

## Key Configuration Files

- **_env**: Environment variables (copy from _env.template)
- **docker-compose.yml**: Docker services configuration
- **pyproject.toml**: Python dependencies and project configuration
- **uv.lock**: Locked dependency versions for reproducible builds
- **pytest.ini**: Test configuration with markers and settings
- **Thoth/settings.py**: Django settings

## Database Architecture

### SQL Databases
- Managed through thoth-dbmanager library
- Supports PostgreSQL, MySQL, SQLite, MariaDB, SQL Server, Oracle
- Connection details stored in SqlDatabase model

### Vector Databases  
- Managed through thoth-vdbmanager library
- Supported options: Qdrant (primary), Milvus, Chroma, PGVector
- Stores:
  - Hints for SQL generation
  - Question/SQL pairs for few-shot learning
  - Table/column descriptions
  - Generic semantic documentation

## AI Workflow Components

### Backend AI Components
Located in `thoth_core/thoth_ai/`:
- **Agents**: PydanticAI-based agents for different workflow steps
- **Tools**: Database interaction, query execution, result processing
- **Utilities**: Helper functions for SQL generation and validation

### SQL Generator Service
Located in `frontend/sql_generator/`:
- **FastAPI Service**: Separate service for SQL generation using PydanticAI agents
- **Agent System**: Specialized agents for question validation, translation, keyword extraction, SQL generation, and evaluation
- **Workflow**: 6-phase process for natural language to SQL conversion
- **Main Endpoint**: `/generate-sql` for converting questions to SQL queries

**Note**: The backend and SQL generator communicate via API calls. The backend manages workspaces and metadata, while the SQL generator handles the AI-powered SQL conversion.

## API Endpoints

Main API routes in:
- `thoth_core/urls.py`: Core authentication and management APIs
- `thoth_ai_backend/urls.py`: AI workflow and query execution APIs

Key endpoints:
- `/api/login/`: Authentication
- `/api/workspaces/`: Workspace management
- `/api/preprocess/`: Data preprocessing and management
- `/api/evidence/`: Evidence management for AI training
- `/api/questions/`: Question/SQL pair management
- `/api/columns/`: Database column information

## Important Notes

1. **Environment Setup**: Always copy `_env.template` to `_env` and configure API keys
2. **Docker Network**: Run `./setup-docker.sh` before first Docker run to create network/volumes
3. **Test Isolation**: Tests use separate containers (thoth-test-postgres, thoth-test-qdrant)
4. **Async Tasks**: Background tasks handled by Django's async capabilities
5. **Security**: Token-based authentication required for API access

## Development Workflow

1. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh` (if not already installed)
2. Install dependencies: `uv sync --extra dev`
3. Set up environment: Copy and configure `_env` file
4. Run migrations: `uv run python manage.py migrate`
5. Start development server: `uv run python manage.py runserver` or use Docker containers
6. Access admin at `http://localhost:8040/admin`

## Database Connection Examples

When adding new database connections:
- PostgreSQL: `postgresql://user:password@host:port/dbname`
- MySQL: `mysql://user:password@host:port/dbname`
- SQLite: `sqlite:///path/to/database.db`

Vector database collections are automatically created with matching names to SQL databases.
- from now on remember that THothAI is the name of the project and the license is Apacho 2.0