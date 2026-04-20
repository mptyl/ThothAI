# Configuration Files

The public Docker Compose deployment needs exactly two editable files:

1. `.env.docker`
2. `config.yml.local`

## `.env.docker`

Create it from `.env.compose.template`:

```bash
cp .env.compose.template .env.docker
```

The most important keys are:

| Key | Required | Purpose |
| --- | --- | --- |
| `BUILD_MODE` | Yes | Must remain `hub` for the published Docker Hub flow |
| `DOCKER_REGISTRY` | Usually | Defaults to `tylconsulting` |
| `IMAGE_VERSION` | Usually | Defaults to `latest`; pin it for repeatable deployments |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` | At least one | LLM provider credentials |
| `EMBEDDING_PROVIDER` | Yes | Embedding backend used for vector retrieval |
| `EMBEDDING_MODEL` | Yes | Embedding model name |
| `EMBEDDING_API_KEY` | Usually | Key for the embedding backend |
| `BACKEND_AI_PROVIDER` | Yes | Backend provider used by Django tasks |
| `BACKEND_AI_MODEL` | Yes | Backend model identifier |
| `DJANGO_SUPERUSER_USERNAME` | Yes | Admin user bootstrap |
| `DJANGO_SUPERUSER_PASSWORD` | Yes | Admin password bootstrap |
| `WEB_PORT` | Yes | Main entrypoint exposed by the proxy |
| `FRONTEND_PORT` | Yes | Direct frontend port if needed |
| `SQL_GENERATOR_PORT` | Yes | Direct SQL Generator port if needed |
| `POSTGRES_INTERNAL` | Optional | Keep `true` for the default Compose setup |

## `config.yml.local`

Create it from the tracked template:

```bash
cp config.yml config.yml.local
```

This file controls:

- enabled AI providers
- embedding configuration
- backend default model
- supported database drivers
- admin and demo bootstrap users
- ports and runtime logging defaults
- relevance guard thresholds used by the SQL Generator

## Minimum Recommended Edits

Before the first boot, update:

- at least one provider in `ai_providers`
- `embedding.provider`, `embedding.model`, and its API key
- `backend_ai_model`
- `admin.password`
- any host port overrides if `8040`, `3040`, or `8020` are already occupied

## Sensitive Files

Do not commit:

- `.env.docker`
- `config.yml.local` if it contains real credentials

Keep the tracked files as templates only.
