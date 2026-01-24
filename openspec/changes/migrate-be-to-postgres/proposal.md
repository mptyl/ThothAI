# Change: Migrate Backend Database to PostgreSQL

## Why
Currently, ThothAI uses SQLite for its backend database, which is unsuitable for production-grade distributed environments (like Docker Swarm) due to concurrency and persistence limitations. PostgreSQL provides the necessary scalability and distributed support required for the platform's evolution.

## What Changes
- **BREAKING**: Django configurations will switch to PostgreSQL as the default engine when configured.
- New environment variables for database credentials in `.env.local` and `.env.docker`.
- Addition of an internal PostgreSQL service in `docker-compose.yml` and `docker-stack.yml`.
- Logic to toggle between internal and external PostgreSQL instances.

## Impact
- Affected specs: `db-config`
- Affected code: `backend/Thoth/settings.py`, `.env.*.template`, `docker-compose.yml`, `docker-stack.yml`
