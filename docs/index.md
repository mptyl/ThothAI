# Welcome to ThothAI

ThothAI is a multi-service Text-to-SQL platform that turns natural-language questions into validated SQL through a combination of workspace configuration, schema retrieval, agent orchestration, and query evaluation.

This documentation is now published directly from the main repository and reflects the current runtime contract of the application.

## What This Site Covers

- the supported Docker Compose installation path based on Docker Hub images
- the configuration files required to boot the stack
- the current backend, frontend, SQL Generator, and vector database architecture
- the runtime roles of the configured agents
- the actual data-linking and SQL testing flow implemented in the current codebase

## Product Shape

ThothAI is built from these main runtime components:

- a Django backend for configuration, metadata, and admin-driven setup
- a Next.js frontend for workspace-driven query interaction
- a FastAPI SQL Generator for retrieval, generation, evaluation, and response streaming
- a Qdrant vector database for evidence and example retrieval

## Reading Order

1. Start with [Docker Compose From Docker Hub](installation/docker-compose.md).
2. Review the required [Configuration Files](installation/configuration-files.md).
3. Follow the [First Workspace](quickstart/getting-started.md) walkthrough.
4. Use the SQL Generation section to understand the runtime pipeline and evaluation model.

## Scope

The public site intentionally excludes:

- source installation
- hybrid local development
- Docker Swarm deployment
- Italian-only published pages
- legacy workflow descriptions that do not match the current supported runtime

Those materials are preserved in the repository archive under `legacy-docs/`, but they are not part of the published navigation.

 

