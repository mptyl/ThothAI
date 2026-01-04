# Management and Maintenance (CLI Management)

This document describes CLI commands for daily ThothAI management, including monitoring, cleanup, and automatic updates.

## 1. Status Monitoring

To view the health status of containers and services:

### Docker Compose (Single Node)
```bash
# Local
uv run thothai status

# Remote
uv run thothai status --server ssh://user@ip
```

### Docker Swarm
```bash
# Local
uv run thothai swarm status

# Remote
uv run thothai swarm status --server ssh://user@ip
```

It will show the list of services, status (Running/Stopped), and replicas.

## 2. Application Update

To update the application to a new version specified in `config.yml.local`:

1.  Modify `config.yml.local` (if needed).
2.  Rerun deployment:

```bash
# Compose
uv run thothai up [--server ...]

# Swarm
uv run thothai swarm deploy [--server ...]
```

## 3. Automatic Updates (Watchtower)

You can configure ThothAI to update automatically when new images are published (e.g., security patches).

This uses **Watchtower**, a service that monitors for new images.

### Configuration
Refer to example files or add a `watchtower` service to your `docker-compose.yml` or Swarm stack.

Example command for automatic update on Compose (thoth services only):
```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 3600 \
  --cleanup \
  thoth-backend thoth-frontend thoth-sql-generator thoth-proxy
```

## 4. Cleanup (Prune)

Over time, Docker can accumulate old images, unused volumes, and orphaned networks. The `prune` command helps free up space.

### Execution
```bash
# Local
uv run thothai prune

# Remote
uv run thothai prune --server ssh://user@ip
```

This command will remove:
*   Stopped containers.
*   Unused networks.
*   Dangling images (untagged).
*   (Optional) Unused volumes (be careful with data!).

## 5. Viewing Logs

The CLI does not (yet) have a unified native `logs` command, but you can use standard Docker commands combined with SSH connection if needed.

```bash
# Manual example on remote
ssh user@ip "docker logs -f thoth-backend"
```
