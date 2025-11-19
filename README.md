# ThothAI - Unified Text-to-SQL Platform

<div align="center">
  <img src="frontend/public/dio-thoth-dx.png" alt="ThothAI Logo" width="200"/>
  
  **Advanced AI-powered Text-to-SQL generation platform**
  
  [![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
  [![Python](https://img.shields.io/badge/Python-3.13-green.svg)](https://www.python.org/)
  [![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
</div>

## 📚 Official Documentation

Full documentation is available at: [https://thoth-ai.readthedocs.io](https://thoth-ai.readthedocs.io)

## 🚀 Quick Start

### Docker Installation (Recommended)

For the complete step-by-step guide, see: [Docker Installation Guide](docs/DOCKER_INSTALLATION.md). On Windows, refer also to [Windows Installation (WSL-based)](docs/WINDOWS_INSTALLATION.md).

```bash
# 1. Clone the repository
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI

# 2. Copy and configure environment file
cp config.yml config.yml.local
# Edit config.yml.local with your API keys and configuration

# 3. Run the installer
./install.sh                 # Linux/macOS
# Windows (CMD or PowerShell): .\install.bat  (or .\install.ps1)

# 4. Start all services (if not already started by installer)
docker compose up -d

# 5. Access the application
# Frontend: http://localhost:3040
# Backend Admin: http://localhost:8040/admin
# API: http://localhost:8040/api
```

### Local Development Setup

```bash
# 1. Prerequisites
# Install uv for Python management
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Copy and configure the unified config (if you haven't done it yet)
cp config.yml config.yml.local
# Edit config.yml.local with your API keys, embeddings, database flags, and ports.
# This file is now the single source of truth for BOTH Docker and local development.

# 3. (Optional) Override DB root path for the current shell
export DB_ROOT_PATH=/absolute/path/to/your/dev_databases  # Directory containing BIRD test databases

# 4. Start all services locally (auto-generates .env.local and syncs Python deps)
./start-all.sh

# 5. Access services
# Frontend: http://localhost:3200
# Backend: http://localhost:8200
# SQL Generator: http://localhost:8180
# Qdrant: http://localhost:6334
```

## 📋 Prerequisites

- Docker & Docker Compose v2 (for Docker installation)
- Python 3.13+ with uv (for local development)
- At least one LLM API key (OpenAI, Gemini, or Anthropic)
- 4GB RAM minimum
- 5GB disk space

## 🪟 Windows Line Endings (CRLF vs LF)

This repository enforces line endings via a root `.gitattributes` so fresh clones on Windows do not suffer from `^M` issues when building Docker images.

- Policy: all code, shell scripts, Dockerfiles, and YAML use LF; PowerShell scripts (`*.ps1`) use CRLF for native Windows usage; binary assets are marked `-text`.
- Fresh clones: no action required. Git writes the correct EOL for each file; the installer no longer rewrites line endings.
- Existing clones that predate this change: after pulling the commit that introduces `.gitattributes`, perform a one-time cleanup:
  - No local edits: `git reset --hard`
  - With local edits: `git stash`, `git pull`, then `git stash pop`

If your editor forces CRLF on LF-managed files, configure it to respect `.gitattributes` (or set per-project settings to keep LF for `*.sh`, `Dockerfile*`, `*.yml`, etc.).

## 🏗️ Project Structure

### Primary Directory Structure
```
ThothAI/
├── backend/              # Django backend (API & Admin)
├── frontend/             # Next.js frontend + SQL Generator
├── docker/               # Dockerfiles for all services
├── scripts/              # Utility and deployment scripts
├── config.yml.template   # Configuration template
├── docker-compose.yml    # Service orchestration
└── install.sh           # Interactive installer
```

### Secondary Directory Structure
```
backend/
├── thoth_core/          # Core models, admin interface
├── thoth_ai_backend/    # AI workflow implementation
├── tests/               # Test suites
└── logs/               # Backend logs (local only)

frontend/
├── sql_generator/       # FastAPI SQL generation service
│   ├── agents/         # PydanticAI agents (Core, Tools, Validators)
│   └── logs/          # SQL generator logs (local only)
├── src/                # Next.js application source
└── public/            # Static assets
```

## 📂 Data Management

### setup_csv/
- **Purpose**: Initial configuration data for system setup
- **Contents**: CSV files with default models, users, database structures
- **Usage**: Loaded via `python manage.py load_defaults` command
- **Docker**: Copied during build, not bind-mounted
- **Structure**: `local/` and `docker/` subdirectories for environment-specific configs

### data_exchange/
- **Purpose**: Runtime data import/export between host and containers
- **Contents**: 
  - CSV exports from Django admin
  - Generated PDF documentation
  - Qdrant vector database backups
  - User-provided import files
- **Docker**: Bind-mounted at `/app/data_exchange`
- **Local**: Used directly from project root

### DB_ROOT_PATH Configuration
- **Purpose**: Points to directory containing BIRD test databases
- **Format**: Absolute path to directory with `dev_databases/` subdirectory
- **Example**: `/Users/username/test_data` containing `dev_databases/*.json`
- **Usage**: Required for SQL generation testing and validation

### SSH Tunnel Support for Databases
- **Enable via Admin**: In Django Admin → *SQL databases*, toggle **SSH Tunnel** to reach databases behind bastion hosts.
- **Credentials**: Supports password, private key, or both. Password/passphrase fields include a visibility toggle (👁️) and are stored server-side without ever hitting logs.
- **Certificates**: Provide an absolute path to the private key stored on the backend host (recommended: mount inside the `thoth-secrets` volume when running via Docker).
- **Security**: Strict host key checking is enabled by default—point to a `known_hosts` file if the bastion key is not already trusted. Logs mask all sensitive values.
- **Connectivity Test**: The existing "Test database connection" admin action now exercises the SSH tunnel before running the probe query.
- **IBM Informix**: SSH tunnel is **required** for Informix databases (uses SSH + dbaccess, no local drivers needed). See [Informix Configuration Guide](docs/INFORMIX_CONFIGURATION_GUIDE.md) for setup instructions.

## 📊 Logging

### Docker Environment
- **Centralized**: All logs collected via Docker logging driver
- **Access**: `docker compose logs [service-name]`
- **Persistence**: Logs maintained by Docker daemon
- **Rotation**: Automatic based on Docker configuration

### Local Development
- **Backend logs**: `backend/logs/`
- **SQL Generator logs**: `frontend/sql_generator/logs/`
- **Frontend logs**: Console output
- **Qdrant logs**: Console output
- **Access**: Direct file access or terminal output

## 🔧 Services

### Core Services

| Service | Purpose | Port (Docker) | Port (Local) |
|---------|---------|---------------|--------------|
| Backend | Django REST API & Admin | 8000 (internal) | 8200 |
| Frontend | Next.js web interface | 3040 | 3200 |
| SQL Generator | FastAPI with PydanticAI | 8020 | 8180 |
| PostgreSQL | Main database | 5432 | 5433 |
| Qdrant | Vector database | 6333 | 6334 |
| Nginx Proxy | Reverse proxy | 8040 (external) | - |

### Service Communication
- **Docker**: Services communicate via Docker network
- **Local**: Direct HTTP calls to localhost ports
- **API Gateway**: Nginx proxy (Docker) or direct access (local)

## 🤖 SQL Generation Process

ThothAI uses a sophisticated multi-agent architecture powered by PydanticAI for intelligent SQL generation:

1. **Question Analysis**: 
   - **Validator Agent**: Checks if the question is relevant to the database.
   - **Translator Agent**: Translates non-English questions to English/SQL context.
   - **Keyword Extractor**: Identifies key entities and terms.
2. **Schema Retrieval**: LSH-based schema matching + vector similarity search to find relevant tables and columns.
3. **SQL Generation**: 
   - **SQL Agents (Basic/Advanced/Expert)**: Specialized agents generate SQL candidates based on complexity.
4. **Validation & Selection**: 
   - **Test Generator Agent**: Creates validation tests based on the question and schema.
   - **Evaluator Agent**: Validates SQL candidates against generated tests.
   - **Selection Logic**: Selects the best performing query (Gold/Silver status).
5. **Execution & Formatting**: Query execution with result pagination and explanation via **Explainer Agent**.

### Agent System
- **question_validator_agent**: Validates user questions for relevance and safety.
- **question_translator_agent**: Handles multi-language support.
- **keyword_extraction_agent**: Extracts domain-specific keywords.
- **sql_basic/advanced/expert_agent**: Tiered agents for generating SQL queries of varying complexity.
- **test_gen_agent**: Generates unit tests to validate SQL candidates.
- **evaluator_agent**: Evaluates SQL performance against tests.
- **sql_explainer_agent**: Generates human-readable explanations of the SQL logic.

## 🔧 Configuration

### Required Environment Variables

```env
# LLM API Keys (at least one required)
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-anthropic-key

# Embedding Service
EMBEDDING_API_KEY=your-embedding-key
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# Database Path (for testing)
DB_ROOT_PATH=/absolute/path/to/dev_databases

# Optional: Monitoring
LOGFIRE_TOKEN=your-logfire-token
```

## 🔐 Environment Configuration Management

### Configuration File Structure

ThothAI uses a multi-level configuration system to manage different deployment environments:

#### Configuration Files

1. **`config.yml.local`** – Master configuration for Docker installation
   - Contains all settings (API keys, ports, databases, monitoring)
   - Used by `install.sh` to generate `.env.docker`
   - NOT committed to the repository (gitignored)

2. **`.env.docker`** – Automatically generated for Docker
   - Created by `installer.py` based on `config.yml.local`
   - Contains environment variables for Docker Compose
   - Regenerated on each run of `install.sh`

3. **`.env.local`** – Configuration for local development
   - Used by `start-all.sh` for local development
   - Contains the same settings but with local ports
   - Variables exported into the environment for all services

4. **`.env.template`** – Sample template
   - Reference file with all required variables
   - Copy and customize to create `.env.local`

#### Configuration Flows

#### Docker Deploy (install.sh)

```
config.yml.local → installer.py → .env.docker → docker-compose.yml
                ↓                      ↓
         pyproject.toml.local      Container environment variables
```

The process:
1. `install.sh` checks prerequisites and validates `config.yml.local`
2. `installer.py` reads `config.yml.local` and generates:
   - `.env.docker` with all environment variables
   - `pyproject.toml.local` for database extras
3. Docker Compose uses `.env.docker` to configure containers

#### Local Development (start-all.sh)

```
config.yml.local → generate_env_local.py → .env.local
                ↓                  ↓
      update_local_db_dependencies.py → backend/frontend pyproject.toml.local
                ↓
        uv lock --refresh && uv sync (per directory)
                ↓
.env.local → env validation → export variables → Processes inherit environment
           ↓                   ↓                      ↓
   BACKEND_AI_* check       (filter out PORT=)     Django, SQL Gen, Frontend
```

The process:
1. `start-all.sh` regenerates `.env.local` from `config.yml.local` via `scripts/generate_env_local.py`
2. Database support extras are resolved by `scripts/update_local_db_dependencies.py`, which updates both `backend/pyproject.toml.local` and `frontend/sql_generator/pyproject.toml.local`
3. Whenever dependencies change, `start-all.sh` runs `uv lock --refresh && uv sync` inside `backend/` and `frontend/sql_generator/`
4. `.env.local` is loaded (excluding the generic PORT) and validated via `scripts/validate_backend_ai.py --from-env`
5. Each service inherits the environment variables:
   - Django: uses the variables directly
   - SQL Generator: receives a specific PORT (8180)
   - Frontend: receives a specific PORT (3200)

Important: keep `config.yml.local` as the authoritative configuration. `start-all.sh` will regenerate `.env.local` and sync Python dependencies automatically whenever the YAML changes.

### Python Management with uv

The project uses `uv` to manage Python consistently:

- **Python version**: 3.13.5 (managed by uv, not system Python)
- **`.python-version` files**: in each directory to pin the version
- **Virtual environments**: created with `uv venv` using uv-managed Python

### Best Practices

1. **Never commit** files containing credentials (`.env*`, `config.yml.local`)
2. **Use `config.yml.local`** for Docker, `.env.local` for local development
3. **Do not modify** `.env.docker` manually (it is regenerated automatically)
4. **Back up configurations** before major upgrades

## 📝 Notes

### Important Considerations
- **API Keys**: Never commit API keys to version control
- **Database Path**: DB_ROOT_PATH must be absolute path for test databases
- **Port Conflicts**: Check port availability before starting services
- **Docker Network**: Created automatically by docker-compose
- **Python Version**: Managed by uv, not system Python
- **Log Files**: Local logs not shared with Docker containers

### Common Issues
- **Port conflicts**: Update ports in config.yml.local or .env.local
- **API key errors**: Ensure at least one LLM provider configured
- **Docker build fails**: Check Docker daemon is running
- **Qdrant connection**: Verify port 6333/6334 is available
- **Test failures**: Ensure DB_ROOT_PATH points to valid test databases

## 🚢 Deployment

### Building for Production

```bash
# Build multi-architecture image
docker compose build --pull --no-cache

# Build locally
docker compose build
```

### Docker Hub Publishing

```bash
# Requires Docker Hub account
docker login
./scripts/build-unified.sh v1.0.0
```

## 🔒 Security

- All API keys should be kept secure and never committed to version control
- Use strong passwords for database and admin accounts
- Enable HTTPS in production environments
- Regularly update dependencies

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE.md](LICENSE.md) file for details.

## 👥 Authors

- **Marco Pancotti** - *Initial work* - [GitHub](https://github.com/mptyl) | [LinkedIn](https://www.linkedin.com/in/marcopancotti/)

## 🙏 Acknowledgments

- [PydanticAI](https://ai.pydantic.dev/) for the AI agent framework
- [Django](https://www.djangoproject.com/) and [Django REST Framework](https://www.django-rest-framework.org/) for the backend API
- [Next.js](https://nextjs.org/) and [React](https://react.dev/) for the frontend
- [FastAPI](https://fastapi.tiangolo.com/) for the SQL generation service
- [Qdrant](https://qdrant.tech/) for vector search capabilities
- [SQLAlchemy](https://www.sqlalchemy.org/) for database abstraction
- [Tailwind CSS](https://tailwindcss.com/) for styling
- [AG-Grid](https://www.ag-grid.com/) for data visualization
- [Docker](https://www.docker.com/) for containerization

## 📖 Citation

If you use this work in your research or projects, please consider citing:

```bibtex
@article{talaei2024chess,
  title={CHESS: Contextual Harnessing for Efficient SQL Synthesis},
  author={Talaei, Shayan and Pourreza, Mohammadreza and Chang, Yu-Chen and Mirhoseini, Azalia and Saberi, Amin},
  journal={arXiv preprint arXiv:2405.16755},
  year={2024}
}
```

## 📞 Support

- GitHub Issues: [https://github.com/mptyl/ThothAI/issues](https://github.com/mptyl/ThothAI/issues)
- Email: mp@tylconsulting.it  
---

<div align="center">
  Made with ❤️ by the Tyl Consulting Team
</div>
