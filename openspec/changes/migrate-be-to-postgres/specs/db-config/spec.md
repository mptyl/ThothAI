# Capability: db-config

## ADDED Requirements

### Requirement: Support PostgreSQL in Django
The Django backend MUST be able to connect to a PostgreSQL database if configured via environment variables.

#### Scenario: Connect to External PostgreSQL
- **WHEN** environment variables `DB_ENGINE=django.db.backends.postgresql` and valid connection details (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) are set.
- **THEN** it must successfully connect to the external PostgreSQL instance.

#### Scenario: Fallback to SQLite
- **WHEN** `DB_ENGINE` is not set or set to `django.db.backends.sqlite3`.
- **THEN** it must use the local SQLite database as per legacy configuration.

### Requirement: Internal PostgreSQL Container
In Docker environments, the system SHALL provide an internal PostgreSQL container if requested.

#### Scenario: Start Internal PostgreSQL
- **WHEN** `POSTGRES_INTERNAL=true` in `.env.docker`.
- **THEN** a `db` service running PostgreSQL must be started, and the `backend` must wait for it to be healthy.

#### Scenario: Use External PostgreSQL in Docker
- **WHEN** `POSTGRES_INTERNAL=false` in `.env.docker`.
- **THEN** the `db` service should not be used by the backend, and the `backend` must connect to the host specified in `DB_HOST`.
