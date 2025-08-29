# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ThothAI UI** is the frontend UI component of the ThothAI ecosystem - an AI-powered natural language to SQL conversion system. This directory is currently empty but is intended to house a modern web frontend that complements the existing Streamlit interface (thoth_sl).

### ThothAI Ecosystem Architecture

ThothAI is a comprehensive AI system with multiple interconnected components:

- **thoth_be** - Django backend for configuration and metadata management
- **thoth_sl** - Streamlit frontend for natural language to SQL interface. Obsolete and not supported anymore
- **thoth_ui** - **This directory** - Future modern web frontend
- **thoth_sqldb2** - Database management library (PyPI package)
- **thoth_vdb2** - Vector database management library (PyPI package)

### Project Location Context

- The frontend is located in the project at ../thothsl
- The backend is located in the project at ../thoth_be
- Core libraries include:
  - ../thoth_sqldb2 (database management and LSH)
  - ../thoth_vdb2 (virtual database manager)

### Core Technologies Stack

**Backend Stack (thoth_be)**:
- Django 5.2 with Django REST Framework 3.16.0
- PostgreSQL with SQLAlchemy 2.0.40
- PydanticAI 0.4.7 for AI agents
- Qdrant vector database integration
- Docker + Nginx deployment

**Frontend Stack (thoth_sl)**:
- Streamlit 1.28.0+ for rapid prototyping interface
- Pandas/NumPy for data processing
- Multiple AI provider integrations (OpenAI, Anthropic, Mistral)

## Common Development Commands

### Installation & Setup
```bash
# Quick installation (from project root)
./install.sh                    # Linux/macOS
install.bat                     # Windows

# Manual Docker setup
./setup-docker.sh
docker-compose up --build
```

### Backend Development (Django)
```bash
cd ../thoth_be
python manage.py runserver      # Development server
python manage.py test           # Run all tests
pytest                          # Run pytest suite
python manage.py migrate        # Apply database migrations
python manage.py collectstatic  # Collect static files
```

### Frontend Development (Streamlit)
```bash
cd ../thoth_sl
streamlit run ThothAI.py       # Start Streamlit interface
pytest                         # Run frontend tests
```

### Docker Operations
```bash
# Start all services
docker-compose up --build

# Individual service management
cd ../thoth_be && docker-compose up thoth-be
cd ../thoth_sl && docker-compose up thoth-sl

# Check service logs
docker-compose logs thoth-be
docker-compose logs thoth-qdrant
```

### Testing Commands
```bash
# Backend tests with specific markers
cd ../thoth_be
pytest tests/ -m unit                    # Unit tests only
pytest tests/ -m integration             # Integration tests only
pytest tests/ -m "not slow"              # Skip slow tests
pytest tests/test_ai_backend.py          # Single test file
pytest --tb=short --disable-warnings     # Concise output

# Frontend tests
cd ../thoth_sl
pytest tests/                            # All frontend tests
```

## Architecture & Code Structure

### High-Level System Design

ThothAI implements a **microservices architecture** with AI-powered natural language processing:

```
┌─────────────────┐    ┌──────────────────┐
│   User Browser  │────│  Nginx Proxy     │
│   (thoth_ui)    │    │  (Port 8040)     │
└─────────────────┘    └──────────────────┘
                                │
                       ┌──────────────────┐
                       │  Django Backend  │
                       │  (thoth_be)      │ 
                       └──────────────────┘
                                │
                   ┌────────────┼────────────┐
                   │            │            │
          ┌─────────────┐ ┌─────────────┐ ┌────────────┐
          │ PostgreSQL  │ │   Qdrant    │ │ Streamlit  │
          │   (5443)    │ │   (6333)    │ │   (8501)   │
          └─────────────┘ └─────────────┘ └────────────┘
```

### AI Processing Pipeline

1. **Natural Language Input** → Question validation and preprocessing
2. **Context Retrieval** → Vector database similarity search (Qdrant)
3. **SQL Generation** → Multi-agent AI workflow using PydanticAI
4. **Query Validation** → Syntax and safety checks
5. **Execution** → Database query execution with result formatting
6. **Response** → Structured results with optional explanations

### Core Libraries & Integration Points

**ThothAI Custom Libraries** (available as PyPI packages):
- `thoth-dbmanager[postgresql,sqlite]` - SQL database management with LSH similarity search
- `thoth-vdbmanager[qdrant]` - Vector database abstraction layer

**Key Integration Patterns**:
- **Authentication**: Django Allauth with multi-tenant support
- **AI Agents**: PydanticAI-based agents for specialized SQL generation tasks
- **Vector Search**: Semantic similarity for question/SQL pair retrieval
- **Database Abstraction**: Plugin-based support for multiple SQL databases

### Directory Structure Context

```
../thoth_be/                    # Django backend
├── thoth_core/                 # Core models, admin, auth
├── thoth_ai_backend/           # AI processing, vector ops
├── templates/                  # Django templates
├── static/                     # CSS, JS, images
├── tests/                      # Comprehensive test suite
└── manage.py                   # Django management

../thoth_sl/                    # Streamlit frontend
├── agents/                     # AI agent implementations  
├── helpers/                    # Utility functions
├── sql_generation/             # SQL workflow logic
├── templates/                  # Prompt templates
└── ThothAI.py                  # Main Streamlit app

./                              # This directory (thoth_ui)
└── .venv/                      # Virtual environment
```

## Development Context

### Code Standards & Patterns

- **License**: Apache License 2.0 with copyright headers required on all files
- **Python Version**: 3.12+ recommended, 3.8+ minimum
- **Testing**: pytest mandatory with comprehensive test markers
- **Documentation**: Inline documentation expected, Italian/English dual support
- **Code Quality**: Modern Python practices with Pydantic models throughout

### Database Support Architecture

**Primary Databases**: PostgreSQL (production), SQLite (development)
**Planned Support**: MySQL, MariaDB, SQL Server, Oracle
**Vector Databases**: Qdrant (primary), Weaviate, Milvus via plugin system

### AI Provider Integration

The system supports multiple AI providers through a unified interface:
- OpenAI GPT models
- Anthropic Claude models  
- Mistral AI models
- Extensible architecture for additional providers

### Service Endpoints

- **Backend Django**: http://localhost:8040
- **Admin Panel**: http://localhost:8040/admin  
- **Streamlit Frontend**: http://localhost:8501
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **PostgreSQL**: localhost:5443

## Development Notes

### Current State

The thoth_ui directory is currently empty and ready for frontend development. Based on the ecosystem, this should be a modern web interface that:

- Provides an alternative to the Streamlit interface
- Integrates with the Django backend via REST API
- Offers enhanced user experience for natural language to SQL conversion
- Supports multi-tenant authentication and workspace management

### Integration Requirements  

When developing in thoth_ui, ensure:
- Authentication integrates with Django backend (localhost:8040)
- API calls follow the existing REST framework patterns
- Vector database operations use the thoth-vdbmanager library
- Database connections utilize the thoth-dbmanager library
- Testing follows the established pytest patterns with appropriate markers

### Recommended Technologies

Given the existing stack, consider:
- **React/Next.js** or **Vue.js/Nuxt.js** for modern framework compatibility
- **TypeScript** for type safety matching Python patterns
- **Tailwind CSS** or similar for rapid UI development  
- **React Query** or **SWR** for API state management
- **Docker** integration matching existing deployment patterns

## Documentation Files

### Documentation Standard Points

- The requirements document is REQS.md 
- The previous steps document is PREVIOUS_STEPS.md

## Memories

### Backend Configuration
- l'indirizzo del server ThothAI di backend è in .env.local sotto DJANGO_SERVER=

### Python Development
- usa sempre uv per gestire le dipendenze

### Docker Development
- non testare docker se non esplicitamente richiesto dai requirements

### Frontend Development
- never hardcode the django server url. Always use env.local or env.production

### Dependency Management
- questo è un progetto uv. Tienine conto per la gestione delle dipendenze e in generale per la gestione dell'ambiente

### PydanticAI Template Rules
- **System prompts**: Possono usare `ctx.deps` per dependency injection (es: `{{ctx.deps.question}}`)
- **User prompts**: DEVONO usare placeholder normali `{variable}` e essere formattati con `TemplateLoader.format()` PRIMA di essere passati agli agent
- I placeholder `ctx.deps` NON funzionano negli user prompt, solo nei system prompt
- Sempre usare `TemplateLoader.format('template_name', variable=value)` per gli user template, MAI `TemplateLoader.load()`

### Environment Configuration
- guarda sempre alla radice del progetto per trovare i file .env.*
- quando devi testare il sql_generator proponimi sempre di utilizzare │   curl -X POST "http://localhost:8005/generate-sql" \                                                                      │
│     -H "Content-Type: application/json" \                                                                                  │
│     -d '{                                                                                                                  │
│       "workspace_id": 4,                                                                                                   │
│       "question": "How many schools with an average score in Math greater than 400 in the SAT test are exclusively         │
│   virtual?",                                                                                                               │
│       "username": "marco",                                                                                                 │
│       "functionality_level": "BASIC",                                                                                            │
│       "flags": {                                                                                                           │
│         "use_schema": true,                                                                                                │
│         "use_examples": true,                                                                                              │
│         "use_lsh": true,                                                                                                   │
│         "use_vector": true                                                                                                 │
│       }                                                                                                                    │
│     }' 2>/dev/null
- quando ti chiedo di testare l'applicazione chiedimi sempre se sotto docker o in locale. Dopodichè gestisci l'environment di conseguenza
- Quando fai una curl falla senza il formatting JSON per vedere la risposta raw
- questo progetto è sotto uv
- prima di eseguire un test su questo progetto ricordami di accendere qdrant su porta 6334, se trovi il servizio spento
- prima di eseguire il test ricordami di accendere il servizio di backend django sulla porta 8200, se la trovi spenta
- prima di eseguire un test fai partire il servizio sql_generator sulla porta 8001, in locale
- Per testare l'API di sql_generator usa sempre "functionality_level" e NON "sql_generator" nel JSON body
- se non esplicitamente dichiarato, i test vanno sempre intesi in locale
- the log to thoth_be is done using the thth_log_apy.py script int main_helpers
- se non specificato diversamente, sto testando in locale. Quando sto testando su docker lo dichiaro
- ogni nuovo file deve riportare la dicitura di licenza Apache 2.0, non MIT
- from now on remember that the bneme of the project is ThothAI and the licence is Apache 2.0
- non mettere mai le note di copyright nei templates da te generati