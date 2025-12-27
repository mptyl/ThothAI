# thothai-data-cli - Testing Guide

## Table of Contents

1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Test Scenario 1: Local Docker Compose](#test-scenario-1-local-docker-compose)
4. [Test Scenario 2: Local Docker Swarm](#test-scenario-2-local-docker-swarm)
5. [Test Scenario 3: Remote Docker via SSH](#test-scenario-3-remote-docker-via-ssh)
6. [Test Checklist](#test-checklist)
7. [Common Issues](#common-issues)

---

## Overview

This guide provides comprehensive testing procedures for `thothai-data-cli` in different deployment scenarios:

1. **Local Docker Compose** - Development environment
2. **Local Docker Swarm** - Production-like local testing
3. **Remote Docker SSH** - Production remote access

---

## Test Environment Setup

### Prerequisites

- Python 3.9+
- uv installed
- Docker installed and running
- ThothAI repository cloned

### Install CLI for Testing

```bash
# Option 1: Install from local wheel
cd cli/thothai-data-cli
uv build
uv pip install dist/thothai_data_cli-1.0.0-py3-none-any.whl

# Option 2: Run from source
uv sync
alias thothai-data="uv run thothai-data"
```

---

## Test Scenario 1: Local Docker Compose

### Setup

```bash
cd /path/to/ThothAI

# Deploy ThothAI with docker-compose
./install.sh
```

Wait for services to start (check with `docker ps`).

### Configure CLI

Run first command to create config:

```bash
thothai-data csv list
```

Configuration prompts:
- Docker connection type: `local`
- Docker mode: `compose`
- Stack/project name: `thothai` (or check with `docker ps` for actual prefix)

Alternatively, manually create `~/.thothai-data.yml`:

```yaml
docker:
  connection: local
  mode: compose
  stack_name: thothai
  service: backend
  db_service: sql-generator

paths:
  data_exchange: /app/data_exchange
  shared_data: /app/data
```

### Test Commands

#### Connection Test

```bash
thothai-data config test
```

Expected output:
```
Testing Docker connection...
✓ Docker connection successful
✓ Found backend container: thothai_backend_1
✓ Found db service container: thothai_sql-generator_1
```

#### CSV Operations

```bash
# Create test file
echo "id,name,value" > test_data.csv
echo "1,Test,100" >> test_data.csv

# Upload
thothai-data csv upload test_data.csv
# Expected: ✓ Uploaded: test_data.csv

# List
thothai-data csv list
# Expected: Shows test_data.csv in listing

# Download
mkdir downloads
thothai-data csv download test_data.csv -o downloads/
# Expected: ✓ Downloaded to: downloads/test_data.csv

# Verify download
diff test_data.csv downloads/test_data.csv
# Expected: No output (files identical)

# Delete
thothai-data csv delete test_data.csv
# Expected: ✓ Deleted: test_data.csv

# Verify deletion
thothai-data csv list
# Expected: test_data.csv no longer listed
```

#### Database Operations

```bash
# Create test database
sqlite3 test_db.sqlite <<EOF
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
INSERT INTO users VALUES (1, 'Test User');
EOF

# Insert
thothai-data db insert test_db.sqlite
# Expected: ✓ Database inserted: test_db
#           Location: /app/data/test_db/test_db.sqlite

# List
thothai-data db list
# Expected: Shows test_db directory

# Remove
thothai-data db remove test_db
# Expected: ✓ Database removed: test_db

# Verify removal
thothai-data db list
# Expected: test_db no longer listed
```

---

## Test Scenario 2: Local Docker Swarm

### Setup

```bash
cd /path/to/ThothAI

# Initialize Swarm (if not already)
docker swarm init

# Deploy stack
./install-swarm.sh
```

Wait for stack to deploy:

```bash
docker stack ps thothai-swarm
```

### Configure CLI

Create/edit `~/.thothai-data.yml`:

```yaml
docker:
  connection: local
  mode: swarm
  stack_name: thothai-swarm
  service: backend
  db_service: sql-generator

paths:
  data_exchange: /app/data_exchange
  shared_data: /app/data
```

### Test Commands

Run same test commands as Scenario 1:

```bash
# Connection test
thothai-data config test
# Expected: Shows thothai-swarm_backend.1.xxx containers

# CSV tests
thothai-data csv list
# ... (same as Scenario 1)

# Database tests
thothai-data db list
# ... (same as Scenario 1)
```

### Verify Swarm-Specific Behavior

```bash
# Check container names include Swarm task ID
docker ps --filter "name=thothai-swarm_backend"
# Expected: thothai-swarm_backend.1.abc123def456

# Scale backend (optional test)
docker service scale thothai-swarm_backend=2

# CLI should still work (connects to any replica)
thothai-data csv list
```

---

## Test Scenario 3: Remote Docker via SSH

### Setup

Requirements:
- Remote server with Docker
- SSH access configured
- ThothAI deployed on remote server (compose or swarm)

### Configure CLI

Create/edit `~/.thothai-data.yml`:

```yaml
docker:
  connection: ssh
  mode: swarm  # or 'compose' depending on remote deployment
  stack_name: thothai-swarm
  service: backend
  db_service: sql-generator

ssh:
  host: production.example.com
  user: deploy
  port: 22
  key_file: ~/.ssh/production_key  # or leave empty for default

paths:
  data_exchange: /app/data_exchange
  shared_data: /app/data
```

### Test SSH Connection

```bash
# Verify SSH access
ssh user@production.example.com docker ps

# Test CLI connection
thothai-data config test
```

Expected output:
```
Testing Docker connection...
✓ Docker connection successful
✓ Found backend container: thothai-swarm_backend.1.xxx
✓ Found db service container: thothai-swarm_sql-generator.1.xxx
```

### Test Commands

Run same test commands as previous scenarios. Note:

- **Upload**: File is SCP'd to remote, then copied into container
- **Download**: File is copied from container to remote `/tmp`, then SCP'd to local
- **Performance**: May be slower due to network transfer

```bash
# CSV tests
thothai-data csv upload test_data.csv
thothai-data csv list
thothai-data csv download test_data.csv -o ./
thothai-data csv delete test_data.csv

# Database tests
thothai-data db insert test_db.sqlite
thothai-data db list
thothai-data db remove test_db
```

---

##Test Checklist

Use this checklist for each deployment scenario:

### Connection

- [ ] `config test` succeeds
- [ ] Backend container found
- [ ] DB service container found

### CSV Operations

- [ ] `csv list` shows existing files
- [ ] `csv upload` successfully uploads file
- [ ] Uploaded file appears in `csv list`
- [ ] `csv download` retrieves file correctly
- [ ] Downloaded file matches original (checksum/diff)
- [ ] `csv delete` removes file
- [ ] Deleted file no longer in `csv list`

### Database Operations

- [ ] `db list` shows existing databases
- [ ] `db insert` successfully inserts database
- [ ] Inserted database appears in `db list`
- [ ] Database accessible from ThothAI application
- [ ] `db remove` removes database
- [ ] Removed database no longer in `db list`

### Configuration

- [ ] `config show` displays correct settings
- [ ] Config file created automatically on first use
- [ ] Manual config file edits are respected

---

## Common Issues

### Container not found

**Problem**: `No container found for service: backend`

**Debug**:
```bash
# List all containers
docker ps

# For Swarm
docker stack ps thothai-swarm

# Check stack_name in config matches deployment
```

**Solution**: Update `stack_name` in `~/.thothai-data.yml`.

### Permission denied on SSH

**Problem**: SSH connection works but Docker commands fail

**Debug**:
```bash
ssh user@host docker ps
```

**Solution**: Add user to `docker` group on remote server:
```bash
sudo usermod -aG docker username
```

### File not found in volume

**Problem**: Upload succeeds but file not visible in ThothAI

**Debug**:
```bash
# Check volume mount
docker inspect <container> | grep -A 5 Mounts

# Check file in container
docker exec <container> ls -la /app/data_exchange
```

**Solution**: Verify `paths.data_exchange` in config matches container mount.

### SSH key not working

**Problem**: SSH authentication fails with key

**Debug**:
```bash
ssh -vvv -i ~/.ssh/key user@host
```

**Solution**:
- Check key file permissions: `chmod 600 ~/.ssh/key`
- Verify key is added: `ssh-add ~/.ssh/key`
- Check config path: `key_file` in `~/.thothai-data.yml`

---

## Performance Benchmarks

### Local Operations (Expected Times)

- CSV upload (1MB): < 1 second
- CSV download (1MB): < 1 second
- Database insert (10MB): < 5 seconds

### Remote Operations (Expected Times)

- CSV upload (1MB): 2-10 seconds (depending on network)
- CSV download (1MB): 2-10 seconds
- Database insert (10MB): 10-30 seconds

---

## Automated Testing Script

Create `test-all.sh`:

```bash
#!/bin/bash
# Automated test script for thothai-data-cli

set -e

echo "=== Testing CSV Operations ==="
echo "id,name" > test.csv
echo "1,Test" >> test.csv

thothai-data csv upload test.csv
thothai-data csv list | grep test.csv
thothai-data csv download test.csv -o ./downloaded.csv
diff test.csv downloaded.csv
thothai-data csv delete test.csv

echo "✓ CSV tests passed"

echo "=== Testing Database Operations ==="
sqlite3 test.sqlite "CREATE TABLE t(id INT);"

thothai-data db insert test.sqlite
thothai-data db list | grep test
thothai-data db remove test

echo "✓ Database tests passed"

# Cleanup
rm -f test.csv downloaded.csv test.sqlite

echo "=== All tests passed! ==="
```

Run with:
```bash
chmod +x test-all.sh
./test-all.sh
```
