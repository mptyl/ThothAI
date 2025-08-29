# ThothAI Docker Orchestrator

This directory contains the unified Docker orchestrator for the complete ThothAI ecosystem, bringing together both `thoth_ui` and `thoth_be` projects in a single, coordinated deployment.

## Overview

The orchestrator provides:
- **Single Command Deployment**: Start the entire ThothAI ecosystem with one command
- **Unified Network**: All services communicate via the `thothnet` Docker network
- **Independent Maintenance**: Individual project docker-compose files remain untouched
- **Proper Dependencies**: Services start in the correct order with proper dependency management

## Architecture

```
┌─────────────────┐    ┌──────────────────┐
│   User Browser  │────│  Nginx Proxy     │
│   (thoth-ui)    │    │  (Port 8040)     │
│  Port 3001      │    └──────────────────┘
└─────────────────┘             │
        │               ┌──────────────────┐
        │               │  Django Backend  │
        └───────────────│  (thoth-be)      │ 
                        └──────────────────┘
                                │
                   ┌────────────┼────────────┐
                   │            │            │
          ┌─────────────┐ ┌─────────────┐ ┌────────────────┐
          │ PostgreSQL  │ │   Qdrant    │ │ SQL Generator  │
          │   (5443)    │ │   (6333)    │ │    (8005)      │
          └─────────────┘ └─────────────┘ └────────────────┘
```

## Services

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| **thoth-ui** | thoth-ui | 3001 | Next.js frontend application |
| **thoth-sql-generator** | thoth-sql-generator | 8005 | FastAPI service for SQL generation |
| **thoth-be-proxy** | thoth-be-proxy | 8040 | Nginx proxy for Django backend |
| **thoth-be** | thoth-be | - | Django backend application |
| **thoth-db** | thoth-db | 5443 | PostgreSQL database |
| **thoth-qdrant** | thoth-qdrant | 6333 | Qdrant vector database |

## Quick Start

### 1. Environment Setup

```bash
# Run the setup script
./orchestrator-setup.sh
```

This script will:
- Check for required environment files
- Create `../thoth_be/_env` from template if missing
- Create Docker network if needed
- Validate configuration

### 2. Start the Complete Stack

```bash
# Start all services
docker-compose -f docker-compose.orchestrator.yml up --build

# Or use the setup script with auto-start
./orchestrator-setup.sh start

# Run in detached mode
docker-compose -f docker-compose.orchestrator.yml up -d
```

### 3. Access the Applications

- **Frontend**: http://localhost:3001
- **Backend Admin**: http://localhost:8040/admin
- **SQL Generator API**: http://localhost:8005/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Environment Configuration

### Required Files

1. **`.env.docker`** (thoth_ui environment)
   - Location: `/Users/mp/Thoth/thoth_ui/.env.docker`
   - Contains API keys, Django server URL, and frontend configuration

2. **`_env`** (thoth_be environment)
   - Location: `/Users/mp/Thoth/thoth_be/_env`  
   - Contains Django settings, database config, and backend API keys
   - Created from `_env.template` if missing

### Important Environment Variables

**Django Connection:**
```bash
# In thoth_ui .env.docker
DJANGO_SERVER=http://thoth-be-proxy:80
NEXT_PUBLIC_DJANGO_SERVER=http://thoth-be-proxy:80

# In thoth_be _env
DJANGO_API_KEY=your-api-key-here
```

**API Keys (configure in both files):**
```bash
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
MISTRAL_API_KEY=your-mistral-key
GEMINI_API_KEY=your-gemini-key
DEEPSEEK_API_KEY=your-deepseek-key
```

## Data Persistence

The orchestrator uses named volumes for data persistence:

- **`postgres-data`**: PostgreSQL database data
- **`static-data`**: Django static files and uploads
- **`thoth-shared-data`**: Shared data between services
- **`qdrant_storage`**: Vector database collections and data

## Network Configuration

All services communicate via the **`thothnet`** bridge network:

- Services use container names for internal communication
- Frontend connects to backend via `thoth-be-proxy:80`
- SQL generator connects to backend via `thoth-be-proxy:80`
- Database connections use container names (`thoth-db`, `thoth-qdrant`)

## Development Workflow

### Individual Project Development

Each project can still be developed independently:

```bash
# thoth_be development
cd ../thoth_be
docker-compose up

# thoth_ui development  
cd /Users/mp/Thoth/thoth_ui
docker-compose up
```

### Orchestrator Commands

```bash
# Start all services
docker-compose -f docker-compose.orchestrator.yml up

# Start with rebuild
docker-compose -f docker-compose.orchestrator.yml up --build

# Start specific services
docker-compose -f docker-compose.orchestrator.yml up thoth-ui thoth-be-proxy

# Stop all services
docker-compose -f docker-compose.orchestrator.yml down

# View logs
docker-compose -f docker-compose.orchestrator.yml logs -f thoth-ui
docker-compose -f docker-compose.orchestrator.yml logs -f thoth-be

# Initialize shared data (run once)
docker-compose -f docker-compose.orchestrator.yml --profile init-only run --rm thoth-data-init
```

## Troubleshooting

### Common Issues

1. **Environment File Missing**
   ```bash
   # Fix: Run setup script
   ./orchestrator-setup.sh
   ```

2. **Network Already Exists**
   ```bash
   # Fix: Remove existing network
   docker network rm thothnet
   ./orchestrator-setup.sh
   ```

3. **Port Conflicts**
   ```bash
   # Check what's using the ports
   lsof -i :3001  # Frontend
   lsof -i :8040  # Backend proxy
   lsof -i :8005  # SQL generator
   lsof -i :5443  # Database
   lsof -i :6333  # Qdrant
   ```

4. **Database Connection Issues**
   ```bash
   # Check database is running
   docker-compose -f docker-compose.orchestrator.yml ps thoth-db
   
   # Check logs
   docker-compose -f docker-compose.orchestrator.yml logs thoth-db
   ```

### Service Dependencies

Services start in this order:
1. **thoth-db** and **thoth-qdrant** (databases)
2. **thoth-be** (Django backend)
3. **thoth-be-proxy** (Nginx proxy)
4. **thoth-sql-generator** (FastAPI service)
5. **thoth-ui** (Next.js frontend)

### Logs and Debugging

```bash
# View all logs
docker-compose -f docker-compose.orchestrator.yml logs

# View specific service logs
docker-compose -f docker-compose.orchestrator.yml logs -f thoth-ui
docker-compose -f docker-compose.orchestrator.yml logs -f thoth-be
docker-compose -f docker-compose.orchestrator.yml logs -f thoth-sql-generator

# Check service status
docker-compose -f docker-compose.orchestrator.yml ps
```

## File Structure

```
thoth_ui/
├── docker-compose.orchestrator.yml    # Main orchestrator file
├── orchestrator-setup.sh              # Setup helper script
├── README-orchestrator.md             # This documentation
├── docker-compose.yml                 # Individual thoth_ui compose (unchanged)
├── .env.docker                        # thoth_ui environment
└── sql_generator/
    └── Dockerfile

../thoth_be/
├── docker-compose.yml                 # Individual thoth_be compose (unchanged)
├── _env                              # thoth_be environment
├── _env.template                     # Template for _env
└── [other thoth_be files]
```

## Security Notes

- API keys are loaded from environment files
- Database credentials are set in the orchestrator
- Services communicate internally via Docker network
- External access is only via exposed ports

## Contributing

When modifying the orchestrator:

1. Keep individual project docker-compose files unchanged
2. Update this README for any configuration changes
3. Test both orchestrator and individual project deployments
4. Update the setup script if new environment variables are added