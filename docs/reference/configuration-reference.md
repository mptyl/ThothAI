# Configuration Reference

## Supported Published Install Artifacts

The public installation path is based on:

- `docker-compose-hub.yml`
- `.env.compose.template`
- `config.yml`

Your local editable files should be:

- `.env.docker`
- `config.yml.local`

## Environment Variables

Use `.env.compose.template` as the base reference.

High-impact groups are:

- deployment and image source
- provider API keys
- embedding settings
- backend model selection
- bootstrap users
- service ports
- database mode
- logging and telemetry

## YAML Configuration

Use `config.yml` as the base reference for `config.yml.local`.

The main sections are:

- `ai_providers`
- `embedding`
- `backend_ai_model`
- `databases`
- `admin`
- `demo`
- `monitoring`
- `ports`
- `docker`
- `runtime`
- `relevance_guard`

## Runtime Dependencies

The supported deployment assumes:

- Docker Compose v2
- Docker Hub access to `tylconsulting/thoth-*`
- Qdrant reachability inside the Compose network
- at least one valid LLM provider
- one valid embedding provider
