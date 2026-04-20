# System Overview

ThothAI is a multi-service Text-to-SQL platform with a Django backend, a Next.js frontend, and a FastAPI SQL Generator.

## Runtime Topology

The supported Docker deployment exposes these services:

- `backend`: Django admin and backend APIs
- `frontend`: Next.js application
- `sql-generator`: FastAPI service that orchestrates retrieval, generation, and selection
- `proxy`: public reverse proxy
- `mermaid-service`: rendering support for Mermaid assets
- `thoth-qdrant`: vector database for retrieval

## Public Entry Points

- `http://localhost:8040`: proxy entrypoint
- `http://localhost:8040/admin`: Django admin
- `http://localhost:3040`: frontend direct port
- `http://localhost:8020/health`: SQL Generator health endpoint

## Code Layout

- `backend/`: Django application and admin-managed configuration
- `frontend/`: Next.js UI
- `frontend/sql_generator/`: FastAPI SQL Generator, agent management, validators, helpers, and pipeline state
- `docker/`: build definitions for all services
- `docs/`: published MkDocs site
- `legacy-docs/`: archived documentation not included in the public site

## Architectural Boundary

The backend owns configuration and metadata persistence.
The SQL Generator owns request orchestration.
The frontend owns interaction flow.
The vector database provides retrieval support, not authoritative configuration.
