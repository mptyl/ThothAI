# Test Plan: Shared-Data Volume Creation

**Objective:** Test what happens when the `thoth-shared-data` Docker volume doesn't exist and needs to be created with test data during installation.

**Date:** 2025-12-25

## Overview

This test simulates a fresh installation scenario where the `thoth-shared-data` volume is missing and must be created by the installation process. The test ensures we can safely restore the original volume after testing.

## Current Architecture Understanding

### Volume Configuration
- **Volume Name:** `thoth-shared-data`
- **Location in Container:** `/app/data`
- **External Volume:** Yes (defined in [`docker-compose.yml`](../docker-compose.yml:208-210)
- **Used By:** `backend` and `sql-generator` services

### Initialization Process
1. **Docker Build:** [`data/`](../data/) directory is copied to `/app/data_temp/` in the backend container (see [`backend.Dockerfile`](../docker/backend.Dockerfile:66-68))
2. **Container Startup:** [`entrypoint-backend.sh`](../backend/entrypoint-backend.sh:24-28) calls [`init-shared-data.sh`](../backend/scripts/init-shared-data.sh)
3. **Data Copy:** [`init-shared-data.sh`](../backend/scripts/init-shared-data.sh:8-42) copies data from `/app/data_temp/` to `/app/data/` (the volume mount) if `dev.json` doesn't exist
4. **Cleanup:** Temporary directory `/app/data_temp/` is removed after copying

### Key Files
- [`docker-compose.yml`](../docker-compose.yml) - Volume definition
- [`install.sh`](../install.sh) - Volume creation and service startup
- [`backend/entrypoint-backend.sh`](../backend/entrypoint-backend.sh) - Container initialization
- [`backend/scripts/init-shared-data.sh`](../backend/scripts/init-shared-data.sh) - Data population logic

## Test Procedure

### Phase 1: Preparation & Backup

```bash
# 1. Verify current services are running
docker ps | grep thoth

# 2. Check current shared-data volume exists
docker volume ls | grep thoth-shared-data

# 3. Backup the current shared-data volume to a tar archive
docker run --rm \
  -v thoth-shared-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/thoth-shared-data-backup-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

# 4. Verify backup was created
ls -lh thoth-shared-data-backup-*.tar.gz

# 5. Inspect current volume contents (for reference)
docker run --rm \
  -v thoth-shared-data:/data \
  alpine ls -laR /data

# 6. Document current volume size
docker volume inspect thoth-shared-data | grep Mountpoint
du -sh $(docker volume inspect thoth-shared-data | jq -r '.[0].Mountpoint')
```

### Phase 2: Stop Services & Remove Volume

```bash
# 7. Stop all Docker Compose services
docker compose down

# 8. Verify services are stopped
docker ps | grep thoth

# 9. Remove the shared-data volume
docker volume rm thoth-shared-data

# 10. Verify volume is removed
docker volume ls | grep thoth-shared-data
# Should return empty or show no results
```

### Phase 3: Fresh Installation Test

```bash
# 11. Run installation script from Docker Hub (this should recreate the volume)
#    IMPORTANT: Do NOT use --build flag to ensure images are pulled from Docker Hub
#    Capture full output to see what messages a new user receives

echo "=== Starting installation from Docker Hub ===" | tee install-test-output.log
date | tee -a install-test-output.log

./install.sh 2>&1 | tee -a install-test-output.log

echo "=== Installation completed ===" | tee -a install-test-output.log
date | tee -a install-test-output.log

# 12. Review the captured output to see what messages the user receives
echo ""
echo "=== Key messages from installation output ==="
grep -i "volume\|shared-data\|initializ\|warning\|attention\|attenzione" install-test-output.log || true

echo ""
echo "=== Full installation output saved to: install-test-output.log ==="

# 13. Check backend logs for initialization messages
docker logs thoth-backend | grep -i "shared-data\|init-shared-data\|Initializing"

# 14. Verify the volume was created
docker volume ls | grep thoth-shared-data

# 15. Verify volume contents
docker run --rm \
  -v thoth-shared-data:/data \
  alpine ls -laR /data

# 16. Verify dev.json exists (key indicator of successful initialization)
docker run --rm \
  -v thoth-shared-data:/data \
  alpine test -f /data/dev_databases/dev.json && echo "SUCCESS: dev.json exists" || echo "ERROR: dev.json missing"

# 17. Verify services are running
docker ps | grep thoth

# 18. Test application accessibility
curl -f http://localhost:8040/admin/login/ || echo "Backend not accessible"
curl -f http://localhost:3040 || echo "Frontend not accessible"
```

### Phase 4: Validation & Cleanup

```bash
# 19. Stop services again
docker compose down

# 20. Remove the newly created test volume
docker volume rm thoth-shared-data

# 21. Restore the original volume from backup
docker run --rm \
  -v thoth-shared-data:/data \
  -v $(pwd):/backup \
  alpine sh -c "tar xzf /backup/thoth-shared-data-backup-*.tar.gz -C /data"

# 22. Verify restore was successful
docker run --rm \
  -v thoth-shared-data:/data \
  alpine ls -laR /data

# 23. Restart services
docker compose up -d

# 24. Verify services are running and accessible
docker ps | grep thoth
curl -f http://localhost:8040/admin/login/
curl -f http://localhost:3040

# 25. Keep backup for a while (optional: delete after verification)
# rm thoth-shared-data-backup-*.tar.gz
```

## Expected Outcomes

### Phase 1 (Backup)
- Volume `thoth-shared-data` exists
- Backup tar.gz file created successfully
- Volume contents documented

### Phase 2 (Cleanup)
- All containers stopped
- Volume `thoth-shared-data` successfully removed
- `docker volume ls` shows no `thoth-shared-data`

### Phase 3 (Fresh Install)
- [`install.sh`](../install.sh) detects volume doesn't exist (line 132-135)
- Volume is created (line 138)
- **Output captured to `install-test-output.log`**
- **Warning message about slow data upload appears (line 143-146):**
  ```
  ⚠️  ATTENZIONE: Caricamento dati in corso...
     I dati di esempio verranno caricati nel volume Docker.
     Questa operazione può richiedere diversi minuti a seconda della velocità del disco.
     L'applicazione sarà disponibile dopo il completamento di questa operazione.
  ```
- Backend container starts and [`init-shared-data.sh`](../backend/scripts/init-shared-data.sh) runs
- Data copied from `/app/data_temp/` to `/app/data/`
- `dev.json` file exists in volume
- All services start successfully
- Application is accessible
- **Full installation log saved for review**

### Expected Messages in install.sh Output

When running `./install.sh` without `--build` flag (Docker Hub mode):

1. **Initial Setup Messages:**
   ```
   ============================================
     Cleaning up Local Services...
   ============================================
   ✓ Local development services stopped
   Generating configuration...
   ✓ Configuration generated
   Using Docker Registry User: [username]
   ```

2. **Image Pull Messages:**
   ```
   ============================================
     Preparing Images...
   ============================================
   Attempting to pull images from Docker Hub...
   ✓ Images pulled successfully from Docker Hub
   ```

3. **Volume Creation Messages:**
   ```
   ============================================
     Starting Services (using docker-compose-hub.yml)...
   ============================================
   Ensuring network and volumes exist...
   ⚠️  ATTENZIONE: Caricamento dati in corso...
      I dati di esempio verranno caricati nel volume Docker.
      Questa operazione può richiedere diversi minuti a seconda della velocità del disco.
      L'applicazione sarà disponibile dopo il completamento di questa operazione.
   ```

4. **Backend Waiting Messages:**
   ```
   ⏳ In attesa che il backend sia pronto...
      Il caricamento dei dati può richiedere tempo (fino a 20 minuti)...
   ```

5. **Completion Messages:**
   ```
   ============================================
     Installation Complete!
   ============================================
   ThothAI is running using docker-compose-hub.yml.
   Frontend: http://localhost:3040
   Backend:  http://localhost:8040
   ```

### Phase 4 (Restore)
- Test volume removed
- Original volume restored from backup
- Services restart successfully
- Application works as before

## Troubleshooting

### If backup fails
```bash
# Check volume mount point
docker volume inspect thoth-shared-data

# Try alternative backup method using temporary container
docker run --name backup-helper \
  -v thoth-shared-data:/source \
  -v $(pwd):/backup \
  alpine tar czf /backup/thoth-shared-data-backup.tar.gz -C /source .
docker rm backup-helper
```

### If volume removal fails
```bash
# Check what's using the volume
docker ps -a | grep thoth

# Force stop any remaining containers
docker stop $(docker ps -q) 2>/dev/null || true
docker rm $(docker ps -aq) 2>/dev/null || true

# Try removal again
docker volume rm thoth-shared-data
```

### If initialization fails
```bash
# Check backend logs
docker logs thoth-backend

# Check if data_temp exists in container
docker exec thoth-backend ls -la /app/data_temp

# Manually run initialization script
docker exec thoth-backend /app/scripts/init-shared-data.sh
```

### If restore fails
```bash
# Verify backup file integrity
tar tzf thoth-shared-data-backup-*.tar.gz | head

# Check volume exists before restore
docker volume create thoth-shared-data

# Try restore with verbose output
docker run --rm \
  -v thoth-shared-data:/data \
  -v $(pwd):/backup \
  alpine sh -c "tar xzvf /backup/thoth-shared-data-backup-*.tar.gz -C /data"
```

## Safety Checklist

Before running the test:
- [ ] All important data in `thoth-shared-data` volume is backed up
- [ ] Backup file is verified and accessible
- [ ] Current application state is documented (screenshots, notes)
- [ ] Sufficient disk space for backup (~2x volume size)
- [ ] No critical work in progress on the application

After the test:
- [ ] Original volume successfully restored
- [ ] All services running normally
- [ ] Application accessible and functional
- [ ] No data loss detected
- [ ] Backup file kept for a grace period (optional)

## Notes

- The backup file will be approximately the same size as the volume
- The initialization process can take up to 20 minutes on first run (as noted in [`install.sh`](../install.sh:155))
- The `dev.json` file is the key indicator that the volume was properly initialized
- The `data_temp` directory is removed after successful initialization to save container space
- The full installation output is captured in `install-test-output.log` for review
- To review the captured output after the test: `cat install-test-output.log`
- To search for specific messages: `grep -i "attenzione\|warning\|volume" install-test-output.log`
