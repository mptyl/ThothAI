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

### ⚡ Lightning Quick Start (Recommended - No Repository Clone)

Install and run ThothAI in minutes without cloning the repository:

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create project directory
mkdir my-thothai && cd my-thothai
uv venv && source .venv/bin/activate

# 3. Install thothai-cli
uv pip install thothai-cli

# 4. Initialize project
uv run thothai init

# 5. Configure (edit config.yml.local with your API keys)
nano config.yml.local

# 6. Deploy
uv run thothai up

# 7. Access the application
# http://localhost:8040
```

📖 **Full Guide**: [docs/thothai_install/LIGHTWEIGHT_INSTALLATION.md](docs/thothai_install/LIGHTWEIGHT_INSTALLATION.md)

---

### 🐳 Docker Installation (For Developers)

For development or customization, clone the repository:

```bash
# 1. Clone the repository
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI

# 2. Copy and configure environment file
# 2. Configure environment
cp .env.compose.template .env.docker
# Edit .env.docker with your API keys and configuration
# By default uses internal DB (POSTGRES_INTERNAL=true)
# To use external DB: set POSTGRES_INTERNAL=false and configure DB_* vars

# 3. Start all services
./docker-up.sh
# Or manually: docker compose up -d

# 4. Access the application
# Main interface: http://localhost:8040
# Frontend: http://localhost:3040
# Backend Admin: http://localhost:8040/admin
```



## 📋 Prerequisites

- Docker & Docker Compose v2 (for Docker installation)
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



## 🔧 Services

### Core Services

| Service | Purpose | Port (Docker) |
|---------|---------|---------------|
| Backend | Django REST API & Admin | 8000 (internal) |
| Frontend | Next.js web interface | 3040 |
| SQL Generator | FastAPI with PydanticAI | 8020 |
| PostgreSQL | Main database | 5432 |
| Qdrant | Vector database | 6333 |
| Nginx Proxy | Reverse proxy | 8040 (external) | - |

### Service Communication
- **Docker**: Services communicate via Docker network
- **API Gateway**: Nginx proxy (Docker)

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

ThothAI uses a simple `.env` file-based configuration system:

#### Configuration Files

1. **`.env.docker`** – Docker configuration (Active)
   - Copy from `.env.compose.template` (Local) or `.env.swarm.template` (Production)
   - NOT committed to the repository (gitignored)

2. **`.env.local`** – Local development configuration
   - Used by `start-all.sh` for native Python/Node.js development
   - Copy from `.env.local.template` and configure
   - NOT committed to the repository (gitignored)

#### Deployment Options

**Option 1: Docker Compose (Local)**
```bash
cp .env.compose.template .env.docker
# Configure keys...
docker compose up -d
```

**Option 3: Local Development (Hybrid)**
```bash
cp .env.local.template .env.local
# Configure keys...
# Start using SQLite (default) or configure DATABASE_URL for PostgreSQL
./start-all.sh
```

**Option 2: Docker Swarm (Production)**
```bash
cp .env.swarm.template .env.swarm
# Configure keys, external DB, and NFS path...
docker stack deploy -c docker-stack.yml thoth
```





### Python Management with uv

The project uses `uv` to manage Python consistently:

- **Python version**: 3.13.5 (managed by uv, not system Python)
- **`.python-version` files**: in each directory to pin the version
- **Virtual environments**: created with `uv venv` using uv-managed Python

### Best Practices

1. **Never commit** files containing credentials (`.env.docker`, `.env.local`)
2. **Use `.env.docker.template`** as starting point for Docker configuration
3. **Use `.env.local.template`** as starting point for local development
4. **Back up configurations** before major upgrades

## 📝 Notes

### Important Considerations
- **API Keys**: Never commit API keys to version control
- **Database Path**: DB_ROOT_PATH must be absolute path for test databases
- **Port Conflicts**: Check port availability before starting services
- **Docker Network**: Created automatically by docker-compose
- **Python Version**: Managed by uv, not system Python
- **Log Files**: Local logs not shared with Docker containers

- **Port conflicts**: Update ports in config.yml.local
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
./push.sh your_username v1.0.0
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
