# thothai-data-cli - User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [CSV Commands](#csv-commands)
6. [Database Commands](#database-commands)
7. [Configuration Commands](#configuration-commands)
8. [Advanced Usage](#advanced-usage)
9. [Troubleshooting](#troubleshooting)

---

## Introduction

`thothai-data-cli` is a command-line tool for managing CSV files and SQLite databases in ThothAI Docker deployments. It supports both local and remote Docker instances running in either Docker Compose or Docker Swarm mode.

---

## Requirements

- **Python**: 3.9 or higher
- **uv**: Package manager (install from https://docs.astral.sh/uv/)
- **Docker**: Active Docker deployment (local or remote)
- **SSH**: For remote Docker access (optional)

---

## Installation

### Step 1: Create Virtual Environment

```bash
# Create a directory for the CLI
mkdir thothai-data && cd thothai-data

# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows PowerShell
```

### Step 2: Install CLI

```bash
uv pip install thothai-data-cli
```

### Step 3: Verify Installation

```bash
thothai-data --help
```

---

## Configuration

### Automatic Configuration

On first use, if no configuration file exists, the CLI will guide you through creating one:

```bash
thothai-data csv list

# Output:
# Config file not found: ~/.thothai-data.yml
# Create configuration file? [y/N]: y
# Docker connection type [local/ssh]: local
# Docker mode [compose/swarm]: swarm
# Stack/project name [thothai-swarm]: thothai-swarm
# ✓ Configuration saved to ~/.thothai-data.yml
```

### Configuration File: `~/.thothai-data.yml`

```yaml
docker:
  connection: local      # 'local' or 'ssh'
  mode: swarm           # 'compose' or 'swarm'
  stack_name: thothai-swarm
  service: backend
  db_service: sql-generator

ssh:  # Only for remote connections
  host: server.example.com
  user: deploy
  port: 22
  key_file: ""  # Optional

paths:
  data_exchange: /app/data_exchange
  shared_data: /app/data
```

### Configuration Options

| Option | Description | Values |
|--------|-------------|--------|
| `connection` | Docker location | `local` (same machine), `ssh` (remote) |
| `mode` | Docker deployment | `compose` (docker-compose), `swarm` (stack) |
| `stack_name` | Container prefix/stack name | String |
| `service` | Backend service name | Default: `backend` |
| `db_service` | Database service name | Default: `sql-generator` |

---

## CSV Commands

CSV files are stored in the `thothai-data-exchange` Docker volume.

### List Files

```bash
thothai-data csv list
```

Example output:
```
Files in /app/data_exchange:
total 48K
drwxr-xr-x 2 root root 4.0K Dec 27 10:00 .
drwxr-xr-x 1 root root 4.0K Dec 27 09:55 ..
-rw-r--r-- 1 root root  12K Dec 27 10:00 export_2024.csv
-rw-r--r-- 1 root root  8.5K Dec 27 09:58 sales_data.csv
```

### Upload File

```bash
thothai-data csv upload myfile.csv
```

Output: `✓ Uploaded: myfile.csv`

### Download File

```bash
# Download to current directory
thothai-data csv download export_2024.csv

# Download to specific directory
thothai-data csv download export_2024.csv -o ./downloads/
```

Output: `✓ Downloaded to: ./export_2024.csv`

### Delete File

```bash
thothai-data csv delete old_data.csv
```

Output: `✓ Deleted: old_data.csv`

---

## Database Commands

SQLite databases are stored in the `thoth-shared-data` Docker volume with the structure: `/app/data/{name}/{name}.sqlite`

### List Databases

```bash
thothai-data db list
```

Example output:
```
Databases in /app/data:
total 12K
drwxr-xr-x 4 root root 4.0K Dec 27 10:00 .
drwxr-xr-x 1 root root 4.0K Dec 27 09:55 ..
drwxr-xr-x 3 root root 4.0K Dec 27 09:56 california_schools
drwxr-xr-x 3 root root 4.0K Dec 27 10:00 hr_database
```

### Insert Database

```bash
thothai-data db insert ./mydb.sqlite
```

This creates:
- Directory: `/app/data/mydb/`
- Database: `/app/data/mydb/mydb.sqlite`

Output:
```
✓ Database inserted: mydb
  Location: /app/data/mydb/mydb.sqlite
```

> **Note**: The database name is derived from the filename (without extension).

### Remove Database

```bash
thothai-data db remove mydb
```

This removes the entire directory `/app/data/mydb/`.

Output: `✓ Database removed: mydb`

---

## Configuration Commands

### Show Configuration

```bash
thothai-data config show
```

Example output:
```
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Setting    ┃ Value         ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Connection │ local         │
│ Mode       │ swarm         │
│ Stack Name │ thothai-swarm │
│ Service    │ backend       │
│ DB Service │ sql-generator │
└────────────┴───────────────┘
```

### Test Connection

```bash
thothai-data config test
```

Example output:
```
Testing Docker connection...
✓ Docker connection successful
✓ Found backend container: thothai-swarm_backend.1.abc123
✓ Found db service container: thothai-swarm_sql-generator.1.def456
```

---

## Advanced Usage

### Remote Docker via SSH

Edit `~/.thothai-data.yml`:

```yaml
docker:
  connection: ssh
  mode: swarm
  stack_name: thothai-swarm

ssh:
  host: production.example.com
  user: deploy
  port: 22
  key_file: ~/.ssh/production_key
```

Then use commands normally:
```bash
thothai-data csv list  # Executes on remote server
```

### Docker Compose Mode

For development environments using docker-compose:

```yaml
docker:
  connection: local
  mode: compose
  stack_name: thothai  # docker-compose project name
```

---

## Troubleshooting

### Config file not found

**Solution**: Run any command to create it interactively, or manually create `~/.thothai-data.yml`.

### Container not found

**Problem**: `No container found for service: backend`

**Solutions**:
1. Check Docker is running: `docker ps`
2. Verify `stack_name` in config matches deployed stack
3. For Swarm: ensure stack is deployed
4. For Compose: ensure containers are running

### SSH connection failed

**Solutions**:
1. Verify SSH access: `ssh user@host`
2. Check `key_file` path in config
3. Ensure Docker is installed on remote server

### Permission denied on upload/download

**Solutions**:
1. Check Docker volume permissions
2. Run Docker with appropriate user permissions
3. For SSH: ensure user has Docker access (`docker` group)

---

## Examples

### Daily Workflow: CSV Export

```bash
# List current files
thothai-data csv list

# Upload new export
thothai-data csv upload ./exports/monthly_report.csv

# Download for analysis
thothai-data csv download monthly_report.csv -o ./analysis/

# Clean up old files
thothai-data csv delete old_export.csv
```

### Database Management

```bash
# Check existing databases
thothai-data db list

# Add new database alongside california_schools
thothai-data db insert ./hr_system.sqlite

# Later, remove if not needed
thothai-data db remove hr_system
```

### Remote Server Management

```bash
# Configure for remote production server
# Edit ~/.thothai-data.yml with ssh settings

# Verify connection
thothai-data config test

# Upload data to production
thothai-data csv upload production_data.csv
```
