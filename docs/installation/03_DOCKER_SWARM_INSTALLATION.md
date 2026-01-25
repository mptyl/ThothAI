# Docker Swarm Installation Guide

**Docker Swarm** is the recommended mode for **production deployments** requiring high availability, scalability, and rolling updates. This guide covers setting up a ThothAI cluster.

## 1. Prerequisites

- A **Manager Node** with Docker installed and initialized as Swarm Manager.
- Worker nodes (optional) joined to the swarm.
- **Shared Storage** (NFS/GlusterFS/EFS) mounted on all nodes (Critical for distributed persistence).
- **SSH Access** to the manager node.

## 2. Swarm Initialization

On your **Manager Node**, initialize the swarm if you haven't already:

```bash
docker swarm init --advertise-addr <MANAGER-IP>
```

## 3. Configuration

### Environment Variables
### Environment Variables
1.  Copy `.env.swarm.template` to `.env.swarm`.
2.  Edit `.env.swarm` to configure:
    - **Shared Storage**: Set `THOTH_DATA_PATH` (e.g., `/mnt/nfs/thothai`).
    - **External Database**: Configure `DB_HOST`, `DB_USER`, `DB_PASSWORD` (Internal DB is not supported in Swarm).
    - **API Keys**: Configure `OPENAI_API_KEY`, etc.

### Docker Secrets (Security)
Swarm uses **Docker Secrets** to securely manage sensitive data. Instead of passing plain text env vars, `docker-up.sh` (or the CLI) automatically converts relevant variables into secrets.

Secrets managed automatically include:
Secrets managed automatically include:
- `thoth_env_config`: The content of your `.env.swarm` file (passed as secret).

## 4. Shared Storage (Critical)

In a Swarm, containers can float between nodes. Standard Docker `local` volumes stay on the specific machine where they were created. **You must use a shared filesystem** if you want data (Database, Vector DB, Logs) to persist consistently across node moves.

### Example NFS Setup

1.  **Mount your NFS share** on all nodes (Manager and Workers) at the same path, e.g., `/mnt/nfs/thothai`.
2.  **Configure `.env.swarm`**: Set `THOTH_DATA_PATH=/mnt/nfs/thothai`.

That's it. The `docker-stack.yml` uses this path to bind mount the necessary directories.



> [!WARNING]
> Without shared storage, if a database container restarts on a different node, it will effectively "reset" to an empty state or the state of that specific node's local volume.

## 5. Deployment

### Method A: Using Helper Script (Recommended)

Our `docker-up.sh` script detects `DEPLOYMENT_MODE=swarm`... well, actually for Swarm we recommend the manual method or ensuring `.env.docker` is a symlink to `.env.swarm` if using the script.

**Recommended Manual Method for Swarm:**

```bash
./docker-up.sh
```

It performs these steps:
1.  Creates the overlay network `thoth-network` (if missing).
2.  Creates/Updates Docker Secrets from your config files.
3.  Deploys the stack defined in `docker-stack.yml`.

### Method B: Manual Deployment

If you want full manual control:

1.  **Create Network**:
    ```bash
    docker network create --driver overlay thoth-network
    ```

2.  **Create Secrets**:
    ```bash
    docker secret create thoth_env_config .env.swarm
    docker config create thoth_env_docker .env.swarm
    ```

3.  **Deploy Stack**:
    ```bash
    docker stack deploy -c docker-stack.yml thoth
    ```

## 6. Management & Scaling

### Check Status
```bash
docker stack services thoth
docker service ls
```

### Scaling Services
To run multiple instances of the backend (stateless):

```bash
docker service scale thoth_backend=3
```

### Logs
Swarm logs are aggregated (if using a log driver) or can be viewed per service:

```bash
docker service logs -f thoth_backend
```

## 7. Update & Rollback

To update the application (e.g., new image version):
1.  Update `IMAGE_VERSION` in `.env.docker`.
2.  Run `./docker-up.sh` again.

Swarm performs a **rolling update** (default: 1 at a time, 10s delay). If the new container fails the healthcheck, Swarm automatically **rolls back** to the previous stable version.
