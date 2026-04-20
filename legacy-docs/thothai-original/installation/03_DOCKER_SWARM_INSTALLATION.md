# Docker Swarm Installation Guide

**Docker Swarm** is the recommended mode for **production deployments** requiring high availability, scalability, and rolling updates. This guide covers setting up a ThothAI cluster.

## 1. Prerequisites

- A **Manager Node** with Docker installed and initialized as Swarm Manager.
- Worker nodes (optional) joined to the swarm.
- **Shared Storage** (NFS/GlusterFS/EFS) mounted on all nodes (Critical for distributed persistence).
- **SSH Access** to the manager node.

> [!TIP]
> **Local Testing on Mac/Windows**: You can test Swarm locally even without NFS. In this case, use an absolute local path for `THOTH_DATA_PATH` (e.g., `/Users/name/thoth_data`). Note that this will only work in a single-node configuration.

## 2. Swarm Initialization

On your **Manager Node**, initialize the swarm if you haven't already:

```bash
docker swarm init --advertise-addr <MANAGER-IP>
```

### Environment Configuration

Swarm settings are split into two files:

1.  **`.env.swarm`**: Application configuration (API keys, DB, etc.).
    - Copy `.env.swarm.template` to `.env.swarm`.
    - Set `THOTH_DATA_PATH` (e.g., `/mnt/nfs/thothai` or a local path for testing).
    - Configure External Database (PostgreSQL).

2.  **`swarm_config.env`**: Swarm infrastructure configuration (Ports, Stack Name).
    - Copy `swarm_config.env.template` to `swarm_config.env`.
    - **Port Remapping**: Change public ports here (e.g., `WEB_PORT`, `FRONTEND_PORT`) if defaults (7000 series) are occupied.
    - Define `STACK_NAME` (default: `thothai-swarm`).

### Docker Secrets (Security)
Swarm uses **Docker Secrets** to securely manage sensitive data. Instead of passing plain text env vars, `docker-up.sh` (or the CLI) automatically converts relevant variables into secrets.

Secrets managed automatically include:
- `thoth_env_config`: The content of your `.env.swarm` file (passed as secret).

> [!NOTE]
> **Configuration Persistence**: Unlike variable data (which resides in shared volumes), Secrets and Configs are stored and replicated by the cluster's manager nodes. This allows containers to be recreated without losing settings, as Swarm automatically injects secrets into every new instance of the service.

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

To simplify the deployment process (handling network, secrets, and configs automatically):

```bash
./docker-swarm-up.sh
```

To reset the environment to "Day 0" (including schema reset):
```bash
./clean-docker-swarm.sh
```

### Method B: Manual Deployment

If you want full manual control, the following steps are executed by the script:

1.  **Initialize Swarm**:
    ```bash
    docker swarm init
    ```

2.  **Create Network**:
    ```bash
    docker network create --driver overlay --attachable thothai-swarm_thoth-network
    ```

3.  **Create Secrets & Configs**:
    ```bash
    docker secret create thothai-swarm_thoth_env_config .env.docker
    docker config create thothai-swarm_thoth_env_docker .env.docker
    ```

4.  **Deploy Stack**:
    ```bash
    docker stack deploy -c docker-stack.yml thothai-swarm
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

## 8. Common Troubleshooting

### `SECRET_KEY` Syntax Error
If you receive bash errors during deployment (e.g., `syntax error near unexpected token`), check that your `SECRET_KEY` in `.env.swarm` does not contain unescaped special characters (like `(`, `)`, `&`).
**Solution**: Use the `./generate-keys.sh` script to generate secure, bash-compatible keys.

### Database Connection Failed (Local)
If containers cannot connect to a local database (e.g., Supabase on Mac) with `Connection refused` using `localhost`:
**Solution**: Set `DB_HOST=host.docker.internal` in `.env.swarm`. This allows containers to reach services on the host machine.

### Supabase Auth Error (Pooler)
If using local Supabase with a pooler (e.g., Supavisor) and getting `Tenant or user not found`:
**Solution**: Check user format. Often with poolers, you must use the `postgres.<tenant_id>` format (e.g., `postgres.athena`) instead of just `postgres`.
