# Log Management - Docker Environment

## Overview

In a Docker environment, ThothAI implements a logging system that combines:
- Real-time visibility via Docker Desktop and `docker logs`
- Persistence on a volume for analysis and backup
- Automatic cleanup via cron job
- Centralized configuration via environment variables

## Logging System Architecture

### Dual Output

Services write logs as follows:

1. Console (stdout/stderr): All services (frontend, backend, sql-generator, proxy) emit logs to the console for immediate visibility in Docker Desktop.
2. Files on a volume: Log persistence on the `thoth-logs` volume is enabled for the `thoth-backend` and `thoth-sql-generator` services, mounted at `/app/logs`. The frontend does not mount the logs volume and typically does not persist to files (stdout only), unless customized.

```yaml
# docker-compose.yml (excerpt)
services:
  backend:
    container_name: thoth-backend
    volumes:
      - thoth-logs:/app/logs

  sql-generator:
    container_name: thoth-sql-generator
    volumes:
      - thoth-logs:/app/logs

volumes:
  thoth-logs:
    name: thoth-logs
```

### Log Structure in the Container

```
/app/logs/                       # Mounted thoth-logs volume
├── thoth.log                    # Backend Django log
├── thoth.log.2025-09-07         # Rotated backend logs (daily)
├── sql-generator.log            # SQL generator log
├── sql-generator.log.1          # Rotated SQL generator logs
└── sql-generator-app.log        # SQL generator application log
```

## Configuration

### Environment Variables

The variables are defined in `.env.docker` (you can start from `.env.docker.template` and parameters in `config.yml.local`):

```bash
# Backend log level (template default: WARNING)
BACKEND_LOGGING_LEVEL=WARNING

# Frontend log level (template default: WARNING)
FRONTEND_LOGGING_LEVEL=WARNING

# Generic log level
LOGGING_LEVEL=WARNING

# Backend database path (isolated)
DB_NAME_DOCKER=/app/backend_db/db.sqlite3

# User data path
DB_ROOT_PATH=/app/data
```

### Logging Levels

- DEBUG: Detailed information (high verbosity)
- INFO: Normal operations
- WARNING: Abnormal but manageable situations (recommended default in production)
- ERROR: Errors that do not stop the system
- CRITICAL: Critical system errors

## Rotation and Automatic Cleanup

### Integrated Cron System

The backend container includes a cron job that automatically performs cleanup:

```bash
# Runs every 6 hours (logging to /var/log/cron.log)
0 */6 * * * cd /app && python manage.py cleanup_logs >> /var/log/cron.log 2>&1
```

### Retention Policy

- Compression: Not used in Docker (volume storage)
- Removal: By default, logs older than 30 days (configurable with `--days`)
- Patterns handled by the `manage.py cleanup_logs` command:
  - `thoth.log.*` (backend)
  - `sql-generator.log.*` (SQL generator)
  - `sql-generator-app.log.*` (SQL generator app)
  - `*.log.*` (other rotated logs)
  - `*.log.gz` (compressed logs, if any)

## Log Monitoring

### Real-time Viewing

```bash
# Backend logs
docker logs -f thoth-backend

# SQL generator logs
docker logs -f thoth-sql-generator

# Frontend logs
docker logs -f thoth-frontend

# Last 100 log lines with timestamp
docker logs --tail 100 -t thoth-backend

# Logs since a specific time
docker logs --since 2h thoth-backend  # Last 2 hours
```

### Accessing Log Files

```bash
# Start a shell in the backend container
docker exec -it thoth-backend bash
cd /app/logs
tail -f thoth.log

# Copy log to the host
docker cp thoth-backend:/app/logs/thoth.log ./thoth-backup.log

# View directly from the host
docker exec thoth-backend tail -n 100 /app/logs/thoth.log
```

## Manual Management

### Manual Cleanup

If needed, you can run cleanup manually:

```bash
# Run the cleanup command
docker exec thoth-backend python manage.py cleanup_logs

# With custom parameters
docker exec thoth-backend python manage.py cleanup_logs --days 3

# Dry-run mode
docker exec thoth-backend python manage.py cleanup_logs --dry-run
```

### Log Backup

To save logs before cleanup or for analysis:

```bash
# Full backup of the log directory
docker cp thoth-backend:/app/logs ./backup-logs-$(date +%Y%m%d)

# Specific file backup
docker cp thoth-backend:/app/logs/thoth.log ./thoth-$(date +%Y%m%d).log
```

## Docker Desktop

### Viewing in Docker Desktop

1. Open Docker Desktop
2. Go to the “Containers” section
3. Click the desired container (`thoth-backend`, `thoth-sql-generator`, `thoth-frontend`, `thoth-proxy`)
4. The “Logs” tab shows real-time output

### Docker Desktop Features

- Search: Use Ctrl+F to search within logs
- Download: Export visible logs
- Clear: Clears the view (does not delete files)
- Auto-scroll: Automatically follows new logs

## Metrics and Statistics

```bash
# Logs volume size
docker volume inspect thoth-logs | grep -A 5 "UsageData"

# Space used in the backend container
docker exec thoth-backend du -sh /app/logs

# File details
docker exec thoth-backend ls -lah /app/logs
```

### Log Analysis

```bash
# Count errors in the last 24 hours
docker exec thoth-backend grep -c "ERROR" /app/logs/thoth.log

# Analyze error patterns
docker exec thoth-backend grep "ERROR" /app/logs/thoth.log | tail -20

# SQL generator statistics
docker exec thoth-sql-generator wc -l /app/logs/sql-generator.log
```

## Best Practices

### Production

1. Keep WARNING as the default level: Balance between detail and performance
2. Monitor volume space: Docker volumes have limits
3. Regular backups: Export important logs before cleanup
4. Centralization: Consider log aggregation for multi-node deployments

### Troubleshooting

1. Temporarily increase the level:
   ```bash
# Edit .env.docker
BACKEND_LOGGING_LEVEL=DEBUG
# Restart the backend service (docker compose uses the service name)
docker compose restart backend
```

2. Post-mortem analysis:
   ```bash
# Save logs for analysis
docker logs thoth-backend > backend-crash.log 2>&1
```

## Troubleshooting

### Logs not visible in Docker Desktop

If logs do not appear in Docker Desktop:

1. Verify the service writes to stdout:
   ```bash
docker exec thoth-backend ps aux | grep python
```

2. Check the logging configuration:
   ```bash
docker exec thoth-backend env | grep LOGGING
```

### Volume full

If the logs volume is full:

1. Immediate cleanup:
   ```bash
docker exec thoth-backend python manage.py cleanup_logs --days 1
```

2. Recreate the volume (data loss):
   ```bash
docker compose down
docker volume rm thoth-logs
docker compose up -d
```

### Cron not working

If automatic cleanup doesn’t work:

1. Check that cron is active:
   ```bash
docker exec thoth-backend service cron status
```

2. Check crontab:
   ```bash
docker exec thoth-backend crontab -l
```

3. Check cron logs:
   ```bash
docker exec thoth-backend cat /var/log/cron.log
```

## Security

### Log Protection

1. Do not expose the logs volume publicly
2. Sanitize logs before sharing (remove API keys, passwords)
3. Restrict access to the volume in production
4. Encrypt backups of sensitive logs
