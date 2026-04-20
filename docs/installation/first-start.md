# First Start And Health Checks

## Start the Stack

```bash
docker compose -f docker-compose-hub.yml up -d
```

## Check Container Status

```bash
docker compose -f docker-compose-hub.yml ps
```

You want all core services to reach a running or healthy state:

- `thoth-backend`
- `thoth-frontend`
- `thoth-sql-generator`
- `thoth-proxy`
- `thoth-mermaid-service`
- `thoth-qdrant`

## Check the Main URLs

- Application: `http://localhost:8040`
- Django admin: `http://localhost:8040/admin`
- Frontend direct port: `http://localhost:3040`
- SQL Generator health endpoint: `http://localhost:8020/health`
- Qdrant: `http://localhost:6333`

If you changed ports in `.env.docker`, use those values instead.

## Inspect Logs

```bash
docker compose -f docker-compose-hub.yml logs -f backend
docker compose -f docker-compose-hub.yml logs -f sql-generator
docker compose -f docker-compose-hub.yml logs -f frontend
```

Use the backend logs when:

- the admin login page does not load
- the initial schema bootstrap fails
- provider credentials are missing or invalid

Use the SQL Generator logs when:

- `/health` is down
- request streaming fails
- vector retrieval or agent initialization fails

## Expected First-Run Tasks

On the first startup the stack may need time to:

- initialize application data
- create or upgrade backend state
- validate provider settings
- prepare the SQL Generator runtime

The backend health check already allows an extended startup window.

## Troubleshooting Baseline

- `401` or provider errors: recheck API keys in `.env.docker` and `config.yml.local`
- UI loads but queries fail: inspect `sql-generator` and `thoth-qdrant`
- admin not reachable: inspect `backend` and `proxy`
- port conflicts: change ports in `.env.docker` and restart the stack
