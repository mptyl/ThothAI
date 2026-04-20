# DATA-EXCHANGE.md

## Overview

ThothAI's data exchange system enables file transfer between external systems and the application using a hybrid approach that supports three deployment scenarios.

## Deployment Scenarios

### 1. Unified Configuration flow (Recommended)
Use `config.yml.local` and `install.sh` for local Docker deployment.

### 2. Single Docker (docker-compose)

Bind mount to `./data_exchange` directory.

**Access Methods:**
- Direct file access (edit files in `./data_exchange/`)
- API endpoints (for remote access)

### 3. Docker Swarm

Named volume `thoth-data-exchange` managed by Docker.

**Access Methods:**
- API endpoints (required - no direct filesystem access)

## Architecture

### Services Using data_exchange

- **Backend**: Read/Write access to `/app/data_exchange`
- **SQL Generator**: Read/Write access to `/app/data_exchange`
- **Frontend**: Read-only access to `/app/data_exchange`
- **Proxy**: Read-only access to `/vol/data_exchange`

## API Endpoints

Available in all deployment scenarios.

### List Files
```
GET /api/data-exchange/list/
Authentication: Required
```

### Upload File
```
POST /api/data-exchange/upload/
Authentication: Required
Content-Type: multipart/form-data
Body: file (binary)
```

### Download File
```
GET /api/data-exchange/download/<filename>/
Authentication: Required
Response: Binary file
```

### Delete File
```
DELETE /api/data-exchange/delete/<filename>/
Authentication: Required
```

## CLI Tool

Use the provided CLI tool for file operations:

```bash
# List all files
python scripts/data-exchange-cli.py list

# Upload a file
python scripts/data-exchange-cli.py upload my_data.csv

# Download a file
python scripts/data-exchange-cli.py download export.csv

# Delete a file
python scripts/data-exchange-cli.py delete old_data.csv
```

## Deployment

### Local Docker Setup
```bash
# Start services
./install.sh

# Access files directly
ls ./data_exchange/
```

### Docker Compose
```bash
# Start services
docker-compose up -d

# Access files directly or via API
ls ./data_exchange/
python scripts/data-exchange-cli.py list
```

### Docker Swarm
```bash
# Deploy stack
docker stack deploy -c docker-stack.yml thoth

# Access files via API only
python scripts/data-exchange-cli.py list
```

The volume is automatically created and managed by Docker.
