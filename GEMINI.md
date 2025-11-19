# ThothAI - Gemini Context

## Project Overview
**ThothAI** is a unified Text-to-SQL platform designed to generate SQL queries from natural language using advanced AI agents.

## Technology Stack
- **Backend**: Django REST Framework (Python)
- **Frontend**: Next.js (React/TypeScript)
- **SQL Generator**: FastAPI with PydanticAI (Python)
- **Database**: PostgreSQL (Application DB), Qdrant (Vector DB)
- **Infrastructure**: Docker Compose, Nginx
- **Package Management**: `uv` (Python), `npm` (Node.js)

## Key Directories
- `backend/`: Django API & Admin
- `frontend/`: Next.js application
- `frontend/sql_generator/`: FastAPI service for SQL generation logic
- `docker/`: Docker configuration files
- `scripts/`: Utility scripts for setup and maintenance
- `setup_csv/`: Initial data for system setup

## Development Workflow

### Configuration
- **Source of Truth**: `config.yml.local` (Gitignored).
- **Docker Config**: `.env.docker` (Generated from `config.yml.local`).
- **Local Config**: `.env.local` (Generated from `config.yml.local`).

### Running Locally
1. **Install Dependencies**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **Setup Config**: `cp config.yml config.yml.local` (edit as needed)
3. **Start Services**: `./start-all.sh`
   - Frontend: http://localhost:3200
   - Backend: http://localhost:8200
   - SQL Generator: http://localhost:8180
   - Qdrant: http://localhost:6334

### Running with Docker
1. **Install**: `./install.sh`
2. **Start**: `docker compose up -d`
   - Frontend: http://localhost:3040
   - Backend Admin: http://localhost:8040/admin

## Important Notes
- **Line Endings**: The project enforces LF line endings via `.gitattributes`.
- **Python Version**: 3.13+ managed by `uv`.
- **Test Data**: `DB_ROOT_PATH` env var must point to the directory containing BIRD test databases for SQL generation testing.
- **SSH Tunnels**: Supported for database connections (configured in Django Admin).

## Architecture Highlights
- **Multi-Agent System**: Uses PydanticAI for SQL generation (Generator, Selector, Reducer agents).
- **Schema Matching**: LSH-based matching + Vector similarity search.
- **Data Exchange**: `data_exchange/` directory for runtime import/export.
