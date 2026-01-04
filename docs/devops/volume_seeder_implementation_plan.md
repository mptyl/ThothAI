# OS-Agnostic Deployment: Volume Seeder Pattern

## Goal
Replace the OS-specific `rsync` over SSH mechanism with a Docker-native "Volume Seeder" pattern. This enables deployment to any Docker host (Linux, Windows Server) and removes host-level dependencies.

## 1. Backend Codebase Refactoring (Prerequisite)
Ensure all backend commands use the flexible `get_setup_csv_path` helper instead of hardcoded paths. This allows the application to find data regardless of where the volume is mounted (e.g., `/setup_csv` vs `/app/backend/setup_csv`).

### [MODIFY] Backend Management Commands
Update the following files in `backend/thoth_core/management/commands/`:
- `import_relationship.py`
- `import_sqldb.py`
- `import_sqlcolumn.py`
- `import_sqltable.py` (if applicable)

**Change:**
```python
# FROM
csv_path = os.path.join(settings.BASE_DIR, "setup_csv", "filename.csv")
# TO
from thoth_core.management.helpers import get_setup_csv_path
csv_path = get_setup_csv_path("filename.csv", "docker")
```

## 2. Docker Manager Implementation

### New Method: `_seed_volumes`
Replace `_rsync_files` in `docker_manager.py` with `_seed_volumes(server)`.

**Logic:**
1.  **Identify Data**: `setup_csv`, `data/dev_databases`.
2.  **Start Helper**: Run a lightweight container (`alpine`) pinned to the manager node, mounting the target volume `thoth-shared-data` at `/data`.
    ```bash
    docker run -d --rm --name thoth-data-seeder \
      -v thoth-shared-data:/data \
      --label com.docker.stack.namespace=thothai-swarm \
      alpine:latest tail -f /dev/null
    ```
3.  **Transfer**: Use `docker cp` (via `subprocess` or python client) to copy local directories into the container.
    ```bash
    docker cp ./setup_csv thoth-data-seeder:/data/
    ```
4.  **Permissions**: Execute `chown -R 1000:1000 /data` inside container to ensure runtime user access.
5.  **Cleanup**: Stop/Remove `thoth-data-seeder`.

### Update `swarm_up`
- Remove call to `_rsync_files`.
- Call `_seed_volumes` after network creation and before stack deployment.
- Ensure `thoth-shared-data` volume is created explicitly or implicitly by the seeder logic if it doesn't exist.

## 3. Stack Configuration
Update `docker-stack.yml` (or the dynamic generation logic in `swarm_up`) to ensure services mount the volume correctly.
- **Backend/SQL-Generator**:
  - Mount `thoth-shared-data` to `/setup_csv` (root).
  - This aligns with `get_setup_csv_path` checking `Path("/setup_csv")`.

## 4. Verification Strategy
1.  **Mock Environment**: Use the existing Docker mock.
2.  **Execution**: `thothai swarm deploy`.
3.  **Validation**:
    - Verify no `rsync` usage.
    - Inspect volume content: `docker run --rm -v thoth-shared-data:/data alpine ls -R /data`.
    - Verify backend import commands succeed (logs).
