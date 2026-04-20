# Log Management - Local Development

## Overview

During local development, ThothAI generates logs for all main services. Log management is optimized to provide detailed insight during debugging while keeping disk space under control.

## Log Structure

Logs are saved in different directories depending on the service:

```
ThothAI/
├── backend/
│   └── logs/
│       └── thoth.log          # Backend Django log
├── frontend/
│   └── sql_generator/
│       └── logs/
│           └── temp/
│               ├── sql-generator.log    # SQL generator log
│               └── thoth_app.log        # Application log
└── logs/                      # Directory for centralized logs (future expansion)
```

## Configuration

### Environment Variables

Logging levels are configurable via the `.env.local` file:

```bash
# Log level for the Django backend
BACKEND_LOGGING_LEVEL=INFO

# Log level for frontend and SQL generator
FRONTEND_LOGGING_LEVEL=INFO
```

### Available Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General operational information (default)
- `WARNING`: Warnings about potential issues
- `ERROR`: Errors that do not stop execution
- `CRITICAL`: Critical errors that may cause interruptions

## Log Rotation

### Backend (Django)

The backend uses `TimedRotatingFileHandler`, which automatically rotates logs:
- Rotation: at midnight
- File pattern: `thoth.log.YYYY-MM-DD`
- Retention: handled manually via cleanup scripts

### SQL Generator

The SQL generator uses `RotatingFileHandler`:
- Maximum size: 10 MB per file
- Backup files: up to 5 (`sql-generator.log.1`, `.2`, etc.)
- Automatic rotation: when the file reaches 10 MB

## Manual Log Cleanup

ThothAI provides two scripts for manual log cleanup:

### Bash Script

```bash
# Cleanup with default settings (keeps 7 days, compresses after 1 day)
./scripts/cleanup-logs.sh

# Specify days to keep and when to compress
./scripts/cleanup-logs.sh 30 3  # Keeps 30 days, compresses after 3

# Dry-run mode (shows what would be done without modifying files)
./scripts/cleanup-logs.sh --dry-run

# Show help
./scripts/cleanup-logs.sh --help
```

### Python Script

```bash
# Cleanup with default settings
python scripts/cleanup_logs.py

# With custom parameters
python scripts/cleanup_logs.py --days 30 --compress-after 3

# Dry-run mode
python scripts/cleanup_logs.py --dry-run

# Show help
python scripts/cleanup_logs.py --help
```

## Script Features

Both scripts offer:

1. **Automatic Compression**: Logs older than the specified period are compressed with gzip
2. **Safe Removal**: Very old logs are permanently removed
3. **Statistics**: Shows space usage before and after cleanup
4. **Dry-Run Mode**: Lets you preview actions without modifying files
5. **Multi-Service Handling**: Cleans logs for all services together

## Best Practices

### During Development

1. **Use DEBUG only when needed**: It generates many logs and can fill the disk quickly
2. **Weekly cleanup**: Run the cleanup script at least once a week
3. **Monitor space**: Periodically check disk space used by logs

### Troubleshooting

To analyze specific issues:

```bash
# View latest backend errors
tail -f backend/logs/thoth.log | grep ERROR

# View real-time logs of the SQL generator
tail -f frontend/sql_generator/logs/temp/sql-generator.log

# Search for a specific pattern in logs
grep "workspace_id" backend/logs/thoth.log*
```

## Monitoring

### Checking Used Space

```bash
# Total space used by logs
du -sh backend/logs frontend/sql_generator/logs

# Details per directory
du -h backend/logs frontend/sql_generator/logs
```

### Log Watching

To monitor logs in real time during development:

```bash
# Backend
tail -f backend/logs/thoth.log

# SQL Generator
tail -f frontend/sql_generator/logs/temp/sql-generator.log

# All logs at once (requires multitail)
multitail backend/logs/thoth.log frontend/sql_generator/logs/temp/*.log
```

## Important Notes

1. **Do not commit logs**: Log directories are already in `.gitignore`
2. **Backup before mass cleanup**: If you have important logs, create a backup before running cleanup
3. **Disk space**: Keep at least 1 GB of free space for proper operation
4. **Performance**: DEBUG log level can impact performance during development

## Troubleshooting

### Logs not generated

If logs are not generated:

1. Verify that the directories exist:
   ```bash
   mkdir -p backend/logs
   mkdir -p frontend/sql_generator/logs/temp
   ```

2. Check permissions:
   ```bash
   chmod 755 backend/logs
   chmod 755 frontend/sql_generator/logs/temp
   ```

3. Verify environment variables in `.env.local`

### Disk space exhausted

If disk space runs out:

1. Run cleanup immediately:
   ```bash
   ./scripts/cleanup-logs.sh 1 0  # Keeps only 1 day
   ```

2. Manually remove older logs:
   ```bash
   find backend/logs frontend/sql_generator/logs -name "*.log.*" -delete
   ```

3. Consider lowering the logging level to WARNING or ERROR