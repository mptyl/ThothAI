# Environment Configuration Strategy

## Overview

ThothAI uses a dual .env file strategy for managing configuration:

- **`.env.local`** - For local development
- **`.env.docker`** - For Docker deployment (including production)

Both files should be placed at the project root (`/Users/mp/Thoth/thoth_ui/`).

## File Structure

```
thoth_ui/
├── .env.local          # Local development configuration
├── .env.docker         # Docker/production configuration
├── .env.local.template # Template for local development
├── .env.docker.template # Template for Docker
└── sql_generator/
    └── .env           # DEPRECATED - for backward compatibility only
```

## Configuration Loading

The `config_manager.py` automatically selects the correct .env file:

1. **Detection**: Checks `DOCKER_CONTAINER` environment variable
2. **Local Development**: If `DOCKER_CONTAINER != true`, loads `.env.local`
3. **Docker/Production**: If `DOCKER_CONTAINER == true`, loads `.env.docker`

## Key Differences

### Local Development (`.env.local`)
```env
# Django Backend
DJANGO_SERVER=http://localhost:8200

# Vector Database
VECTOR_DB_HOST=localhost
VECTOR_DB_PORT=6334

# Server
SERVER_PORT=8001
```

### Docker/Production (`.env.docker`)
```env
# Django Backend
DJANGO_SERVER=http://thoth-be:8040

# Vector Database  
VECTOR_DB_HOST=thoth-qdrant
VECTOR_DB_PORT=6333

# Server
SERVER_PORT=8001
```

## Docker Compose Integration

The `docker-compose.yml` is configured to:
1. Set `DOCKER_CONTAINER=true` in environment
2. Load `.env.docker` via `env_file` directive
3. Use Docker service names for inter-container communication

## Migration from Old Structure

If you have configuration in `sql_generator/.env`:
1. Move local settings to `.env.local`
2. Move Docker settings to `.env.docker`
3. Remove `sql_generator/.env` (kept only for backward compatibility)

## Best Practices

1. **Never commit** `.env.local` or `.env.docker` to version control
2. **Use templates** (`.env.*.template`) for documentation
3. **Keep secrets secure** - use environment-specific API keys
4. **Test both environments** before deployment