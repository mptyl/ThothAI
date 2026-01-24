# Tasks: PostgreSQL Migration

## Phase 1: Configuration
- [ ] Update `backend/Thoth/settings.py` to support PostgreSQL settings.
- [ ] Add PostgreSQL environment variables to `.env.local.template`.
- [ ] Add PostgreSQL environment variables to `.env.docker.template`.

## Phase 2: Docker Integration
- [ ] Add `db` service to `docker-compose.yml`.
- [ ] Update `backend` service in `docker-compose.yml` to depend on `db` and use PG credentials.
- [ ] Add `db` service to `docker-stack.yml`.
- [ ] Update `backend` service in `docker-stack.yml` to depend on `db`.

## Phase 3: Validation
- [ ] Verify local Django startup with external PostgreSQL.
- [ ] Verify Docker Compose startup with internal PostgreSQL (`POSTGRES_INTERNAL=true`).
- [ ] Verify Docker Compose startup with external PostgreSQL (`POSTGRES_INTERNAL=false`).
- [ ] Verify Docker Swarm deployment.

## Dependencies
- PostgreSQL driver `psycopg2-binary` (ensure it's in `pyproject.toml`).
