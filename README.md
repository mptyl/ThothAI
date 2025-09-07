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

```bash
# 1. Clone the repository
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI

# 2. Copy and configure environment file
cp config.yml.template config.yml.local
# Edit config.yml.local with your API keys and configuration

# 3. Run the installer
./install.sh

# 4. Start all services
docker-compose up -d

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

# 2. Copy and configure environment
cp .env.template .env.local
# Edit .env.local with your configuration

# 3. Configure test database path
export DB_ROOT_PATH=/absolute/path/to/your/dev_databases  # Directory containing BIRD test databases

# 4. Start all services locally
./start-all.sh

# 5. Access services
# Frontend: http://localhost:3200
# Backend: http://localhost:8200
# SQL Generator: http://localhost:8180
# Qdrant: http://localhost:6334
```

## 📋 Prerequisites

- Docker & Docker Compose (for Docker installation)
- Python 3.13+ with uv (for local development)
- At least one LLM API key (OpenAI, Gemini, or Anthropic)
- 4GB RAM minimum
- 5GB disk space

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
│   ├── agents/         # PydanticAI agents
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

## 📊 Logging

### Docker Environment
- **Centralized**: All logs collected via Docker logging driver
- **Access**: `docker-compose logs [service-name]`
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

ThothAI uses a multi-agent architecture powered by PydanticAI for intelligent SQL generation:

1. **Question Analysis**: Natural language processing to understand user intent
2. **Schema Retrieval**: LSH-based schema matching + vector similarity search
3. **SQL Generation**: Multiple PydanticAI agents generate candidate queries
4. **Validation & Selection**: Evaluator agent validates syntax and selects best query
5. **Execution & Formatting**: Query execution with result pagination and explanation

### Agent System
- **test_generator_with_evaluator**: Main SQL generation agent
- **sql_selector_agent**: Selects best SQL from candidates
- **test_reducer_agent**: Optimizes test cases

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

## 🔐 Gestione Configurazione Ambiente

### Struttura File di Configurazione

ThothAI utilizza un sistema di configurazione multi-livello per gestire diversi ambienti di deployment:

#### File di Configurazione

1. **`config.yml.local`** - Configurazione master per installazione Docker
   - Contiene tutte le configurazioni (API keys, porte, database, monitoring)
   - Usato da `install.sh` per generare `.env.docker`
   - NON committato nel repository (gitignore)

2. **`.env.docker`** - Generato automaticamente per Docker
   - Creato da `installer.py` basandosi su `config.yml.local`
   - Contiene variabili d'ambiente per Docker Compose
   - Rigenerato ad ogni esecuzione di `install.sh`

3. **`.env.local`** - Configurazione per sviluppo locale
   - Usato da `start-all.sh` per sviluppo locale
   - Contiene le stesse configurazioni ma con porte locali
   - Variabili esportate nell'ambiente per tutti i servizi

4. **`.env.template`** - Template di esempio
   - File di riferimento con tutte le variabili necessarie
   - Da copiare e personalizzare per creare `.env.local`

### Flussi di Configurazione

#### Deploy Docker (install.sh)

```
config.yml.local → installer.py → .env.docker → docker-compose.yml
                ↓                      ↓
         pyproject.toml.local    Variabili ambiente container
```

Il processo:
1. `install.sh` verifica prerequisiti e valida `config.yml.local`
2. `installer.py` legge `config.yml.local` e genera:
   - `.env.docker` con tutte le variabili d'ambiente
   - `pyproject.toml.local` per dipendenze database
3. Docker Compose usa `.env.docker` per configurare i container

#### Sviluppo Locale (start-all.sh)

```
.env.local → export variabili → Processi ereditano ambiente
           ↓                            ↓
    (filtro PORT=)              Django, SQL Gen, Frontend
```

Il processo:
1. `start-all.sh` carica `.env.local` (escluso PORT generico)
2. Esporta variabili nell'ambiente shell
3. Ogni servizio eredita le variabili:
   - Django: usa direttamente le variabili
   - SQL Generator: riceve PORT specifico (8180)
   - Frontend: riceve PORT specifico (3200)

### Gestione Python con uv

Il progetto usa `uv` per gestire Python in modo consistente:

- **Python versione**: 3.13.5 (gestito da uv, non sistema)
- **File `.python-version`**: in ogni directory per specificare versione
- **Virtual environments**: creati con `uv venv` usando Python gestito

### Best Practices

1. **Non committare mai** file con credenziali (`.env*`, `config.yml.local`)
2. **Usare config.yml.local** per Docker, `.env.local` per sviluppo locale
3. **Non modificare** `.env.docker` manualmente (rigenerato automaticamente)
4. **Backup delle configurazioni** prima di aggiornamenti maggiori

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
./scripts/build-unified.sh v1.0.0

# Build locally
docker-compose build
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