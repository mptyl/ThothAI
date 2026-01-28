# Base Docker Swarm Installation Guide

This guide describes how to install **ThothAI** in a **Docker Swarm** cluster using only native Docker commands and the `docker-stack.yml` file.

## 1. Installation Environment Preparation

Before deploying, create a dedicated directory on your manager node and copy the following required files from the repository:

### Required Files Checklist
Ensure you have the following files in your working directory:
- [ ] `docker-stack.yml`: Swarm infrastructure definition.
- [ ] `.env.swarm.template`: Environment variables template (to be copied to `.env.swarm`).
- [ ] `swarm_config.env.template`: Deployment configuration template (ports, registry, etc.).
- [ ] `.thothai-data.yml.template`: Configuration template for `thothai-data-cli` (to be copied to `.thothai-data.yml`).
- [ ] `setup_csv/`: Directory containing base initialization data.

## 2. Infrastructure Prerequisites

Ensure you have:
- A **Docker Swarm** cluster already initialized (`docker swarm init`).
- An **external PostgreSQL database** accessible by the swarm nodes (required for persistence in Swarm).
- **Shared storage** (e.g., NFS) mounted on all nodes at the path specified as `THOTH_DATA_PATH`.
- ThothAI images pushed to an accessible registry or present locally on the nodes.

## 3. Configuration Preparation

1.  Copy the available templates:
    ```bash
    cp .env.swarm.template .env.swarm
    cp swarm_config.env.template swarm_config.env
    cp .thothai-data.yml.template .thothai-data.yml
    ```
2.  Edit `.env.swarm` with your API keys (OpenAI, Anthropic, etc.) and PostgreSQL database credentials.
3.  Edit `swarm_config.env` to configure service ports, stack name, and Docker registry (if needed). This file is used by deployment scripts and for managing exposed ports.
4.  Ensure that `THOTH_DATA_PATH` points correctly to your shared storage.

## 4. Swarm Infrastructure Management

### A. Create Overlay Network
```bash
docker network create --driver overlay --attachable thothai-swarm_thoth-network
```

### B. Create Secrets & Configs
```bash
# Create the secret for environment configuration
docker secret create thothai-swarm_thoth_env_config .env.swarm

# Create the config for the .env.swarm file to be injected into the container
docker config create thothai-swarm_thoth_env_docker .env.swarm
```

## 5. Stack Deployment

```bash
# Export required variables
export THOTH_DATA_PATH=/mnt/nfs/thothai
export IMAGE_VERSION=latest

# Run the deploy command
docker stack deploy -c docker-stack.yml thothai-swarm
```

## 6. Data Initialization (`setup_csv`)

> [!IMPORTANT]
> **No default data included in the image**
> ThothAI Docker images **do not include default data**. Upon first startup, the database will be empty.

### Configuration in Docker Swarm
You must map the `setup_csv` directory so it is accessible to the backend service:

1.  Copy the `setup_csv` directory to shared storage: `${THOTH_DATA_PATH}/setup_csv`.
2.  The `docker-stack.yml` file must include the following volume in the `backend` service:
    ```yaml
    volumes:
      - ${THOTH_DATA_PATH}/setup_csv:/setup_csv
    ```

## 7. Data Exchange Management (`data-exchange`)

The `data-exchange` directory handles CSV exports and imports between different environments.

1.  **Host Path**: `${THOTH_DATA_PATH}/data_exchange` on shared storage.
2.  **Usage**: Files exported from the interface will appear here automatically.

## 8. Using `thothai-data-cli`

The `thothai-data-cli` tool is the recommended way to manage data in the Swarm stack.

### Installation
You can install the CLI directly from PyPI:
```bash
uv pip install thothai-data-cli
```
*Using a virtual environment is highly recommended.*

### Initial Configuration
On the first run, execute the command to interactively generate the configuration:
```bash
thothai-data config show
```
During configuration:
- Choose `swarm` as the mode.
- Enter the stack name (e.g., `thothai-swarm`).
- Choose `local` connection if running from the manager node, or `ssh` to manage the swarm remotely.

### Main Commands
- **Test connection**: `thothai-data config test`
- **List files**: `thothai-data csv list`
- **Upload file**: `thothai-data csv upload my_file.csv`
- **Download exports**: `thothai-data csv download file_name.csv`

---

## 9. Useful Management Commands

### Check Service Status
```bash
docker stack services thothai-swarm
```

### Remove the Stack
```bash
docker stack rm thothai-swarm
docker secret rm thothai-swarm_thoth_env_config
docker config rm thothai-swarm_thoth_env_docker
```
