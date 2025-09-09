# Development Database Sync Guide

## Overview

ThothAI uses a specialized wrapper script (`scripts/sync-to-volume.sh`) to sync development databases from your local filesystem into the Docker volume consumed by the containers. This guide explains how to use it to add new databases to the system.

## Sync Architecture

### How it Works

The `sync-to-volume.sh` wrapper calls the main sync script `scripts/sync-dev-databases.sh`, which performs a non-destructive sync:

1. Reads files from `${DB_ROOT_PATH}/dev_databases/` if `DB_ROOT_PATH` is set in `.env.local`, otherwise from `./data/dev_databases/`.
2. Starts a temporary Alpine container (auto-removed via `--rm`).
3. Mounts the source directory read-only and the `thoth-shared-data` Docker volume as the target.
4. Copies only new files into `thoth-shared-data` at `/target/dev_databases/`.
5. Existing files in the volume are never overwritten (`rsync --ignore-existing` or `cp -rn` fallback).

Security characteristics:

- Non-destructive: existing files are not overwritten.
- Source is mounted read-only.
- Temporary container is automatically removed.
- Interactive confirmation is requested by default (see note on `--force`).
 
## Configuring the Source Directory (DB_ROOT_PATH)

By default, the source directory is `./data/dev_databases` in your project root.

If you set `DB_ROOT_PATH` in `.env.local`, the source becomes:

- `${DB_ROOT_PATH}/dev_databases`

This allows you to keep your development databases outside the repository. The `scripts/sync-to-volume.sh` wrapper automatically loads `.env.local` and passes `DB_ROOT_PATH` to the main sync script.

## Step-by-Step: Add a Database

1) Prepare the directory structure and place your SQLite file:
   - Default: `data/dev_databases/<your_db_name>/`
   - If `DB_ROOT_PATH` is set: `${DB_ROOT_PATH}/dev_databases/<your_db_name>/`

Example layout:

```
data/dev_databases/
└── company_data/
    ├── company_data.sqlite
    └── database_description/
        ├── schema.sql
        ├── sample_queries.sql
        └── README.md
```

## Running the Sync

Interactive (default):

```bash
./scripts/sync-to-volume.sh
```

The wrapper reads `.env.local` and uses `DB_ROOT_PATH` if present.

Force mode:

```bash
./scripts/sync-to-volume.sh --force
```

Important: due to the current implementation in `scripts/sync-dev-databases.sh`, the `--force` flag does not skip the interactive confirmation and, if you confirm, the sync may run twice within the same invocation. Prefer interactive mode until the script is updated to properly bypass the prompt under `--force`.

Dry-run:

```bash
./scripts/sync-to-volume.sh --dry-run
```

Shows what would be synced without making changes.

## Verifying the Sync

From a temporary container:

```bash
docker run --rm -v thoth-shared-data:/data alpine ls -la /data/dev_databases/
```

From inside the backend container:

```bash
docker exec -it thoth-backend bash
ls -la /app/data/dev_databases/
```

## Troubleshooting

Docker volume 'thoth-shared-data' does not exist:

```bash
docker volume create thoth-shared-data
# or
bash backend/setup-docker.sh
```

Source directory does not exist:

```bash
mkdir -p ./data/dev_databases
```

DB_ROOT_PATH issues:

- Ensure `.env.local` exists at the project root and contains an absolute path, e.g.:

```bash
DB_ROOT_PATH=/absolute/path/to/your/dbroot
```

- Ensure the directory `${DB_ROOT_PATH}/dev_databases` exists and contains your databases.

Containers do not see new databases:

1) Ensure the sync completed successfully.
2) If containers were already running, a restart may help:

```bash
docker compose restart backend
```

## Important Notes

- Non-destructive sync; no overwrites.
- Temporary Alpine container is auto-removed.
- No restart required: databases are immediately visible via the mounted volume `thoth-shared-data` at `/app/data` in `backend` and `sql-generator`.
- Any file type can be synced; SQLite is the primary use case.

## References

- Wrapper: `scripts/sync-to-volume.sh`
- Main sync logic: `scripts/sync-dev-databases.sh`
- Compose volume mounts: `docker-compose.yml` (volume `thoth-shared-data` mounted at `/app/data`)
- Environment: `.env.local` with optional `DB_ROOT_PATH` to choose a custom databases root