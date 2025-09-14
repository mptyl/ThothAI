# Windows Installation Guide for ThothAI (WSL-based)

This guide assumes you are on Windows with WSL 2 enabled and Docker Desktop configured to use the WSL backend. All shell commands that use `.sh` scripts should be run inside your WSL distribution. PowerShell commands (e.g., `install.ps1`) are run from Windows PowerShell.

## Prerequisites

Ensure the following are already installed and configured on your system:

- Windows Subsystem for Linux (WSL 2)
- Docker Desktop for Windows with WSL 2 integration enabled
- Git (Windows)

Quick WSL setup (if needed):
```powershell
wsl --install
wsl --set-default-version 2
```

## Installation Steps

### Step 1: Clone the Repository

Use Windows PowerShell to clone the repository (so you can run `install.ps1` or `install.bat`).
```powershell
cd C:\Projects  # or your preferred directory
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI
```

### Step 2: Configure the Application

1. **Copy the configuration template:**
   ```powershell
   Copy-Item config.yml config.yml.local
   ```

2. **Edit `config.yml.local`** with your settings:
   - Add at least one AI provider API key (OpenAI, Anthropic, Gemini, etc.)
   - Configure embedding service (OpenAI, Mistral, or Cohere)
   - Set admin credentials
   - Configure ports if defaults conflict

### Step 3: Run the Interactive Installer

```powershell
./install.bat   # or: .\install.ps1
```

The installer will:
- Validate your configuration
- Create necessary environment files (including `.env.docker`)
- Set up Docker networks and volumes
- Build and start all services

Notes:
- You can re-run `install.ps1` at any time, including after a `git pull`, to rebuild/restart services. This is the recommended update flow on Windows.

### Step 4: Line Endings and Optional Utilities

This repository enforces line endings via `.gitattributes` and `.editorconfig`:

- Code, Dockerfiles, YAML, and shell scripts use LF automatically on checkout.
- PowerShell and Batch scripts use CRLF automatically on checkout.
- Fresh clones require no action for line endings.

Optional utilities (only if building manually without the installer):

- PowerShell: `./scripts/prepare-docker-env.ps1` — create `.env.docker` and prepare folders.
- WSL bash: `./scripts/prepare-docker-build.sh` — legacy helper to normalize EOL; usually unnecessary now.

### Step 5: Start the Services

If you used `install.ps1`, services are already started. To start manually:
```powershell
docker compose up --build

# Or run in background
docker compose up -d --build
```

## Troubleshooting Common Windows Issues

### Issue 1: "No such file or directory" errors

**Cause**: Shell scripts checked out with CRLF in older clones or by external tools.

**Solution**:
- Prefer a fresh clone after the `.gitattributes` introduction.
- Or, in an existing clone, reset files to index (no local edits):
  ```powershell
  git reset --hard
  ```
- If you have local edits to keep: `git stash`, `git pull`, `git stash pop`.

### Issue 2: Missing files during Docker build

**Cause**: Files not synchronized to Git repository

**Solution**:
```powershell
git pull
.\install.ps1
```

### Issue 3: Services stuck during startup

**Cause**: Shell scripts hanging due to line ending issues in older clones

**Solution**:
1. Check container logs:
   ```powershell
   .\scripts\check-docker-logs.ps1
   ```

2. Fix and rebuild (after ensuring proper line endings with `.gitattributes`):
   ```powershell
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

### Issue 4: Port conflicts

**Cause**: Default ports already in use

**Solution**: Edit `config.yml.local` and change the ports:
```yaml
ports:
  backend: 8041     # Instead of 8040
  frontend: 3041    # Instead of 3040
  sql_generator: 8021  # Instead of 8020
```

## Accessing the Application

Once running, access ThothAI at:

- **Web Interface**: http://localhost:3040
- **Admin Panel**: http://localhost:8040/admin
- **API Documentation**: http://localhost:8040/api/docs

Default credentials (if not changed in config.yml.local):
- Username: `admin`
- Password: `admin123`

**⚠️ Important**: Change these credentials immediately after first login!

## Daily Usage

### Starting ThothAI

Preferred ways to start after the first installation:

```powershell
# Re-run installer (recommended, also after updates)
.\install.ps1

# Or start directly
docker compose up -d
```

### Stopping ThothAI

```powershell
# Stop services
docker compose down

# Stop and remove volumes (careful - removes data!)
docker compose down -v
```

### Updating ThothAI

The recommended update flow on Windows is:
```powershell
git pull
.\install.ps1
```
`install.ps1` can be used after the first installation and will handle rebuilding/restarting services as needed.

## Best Practices for Windows

1. **Always use WSL** for running shell scripts
2. **Configure Git** to handle line endings correctly:
   ```bash
   git config --global core.autocrlf input
   ```

3. **Store the project in WSL filesystem** for better performance:
   - Clone to `\\wsl$\Ubuntu\home\username\projects\` when you primarily work from WSL
   - Or keep under `C:\` if you primarily use PowerShell and `install.ps1`

4. **Use PowerShell scripts** when provided (`.ps1` files). `install.ps1` can be re-run after `git pull`.

5. **Monitor Docker resources**:
   - Docker Desktop → Settings → Resources
   - Allocate at least 4GB RAM and 2 CPUs

## Security Considerations

1. **Never commit sensitive files**:
   - `.env.docker` (contains secrets)
   - `config.yml.local` (contains API keys)
   - Any file with API keys or passwords

2. **Use strong passwords**:
   - Change default admin password immediately
   - Use unique API keys for production

3. **Network security**:
   - The application binds to `0.0.0.0` by default
   - Consider using a firewall if exposed to network
   - Use HTTPS proxy for production deployment

4. **Regular updates**:
   ```powershell
   # Check for updates
   git fetch
   git status
   
   # Update if needed
   git pull
   .\install.ps1
   ```

## Getting Help

If you encounter issues:

1. Check the logs:
   ```powershell
   .\scripts\check-docker-logs.ps1
   ```

2. Verify file integrity:
   ```bash
   ./scripts/prepare-docker-build.sh
   ```

3. Clean rebuild:
   ```powershell
   docker-compose down
   docker system prune -f
   docker-compose build --no-cache
   docker-compose up
   ```

4. Report issues at: https://github.com/mptyl/ThothAI/issues

## Quick Reference

### Essential Commands

| Task | Command |
|------|---------|
| First installation / Update | `./install.bat` or `./install.ps1` |
| Optional prep (manual only) | `./scripts/prepare-docker-env.ps1` |
| Line endings | Managed by `.gitattributes` (no manual fix) |
| Start services | `docker compose up -d` |
| Stop services | `docker compose down` |
| View logs | `./scripts/check-docker-logs.ps1` |
| Clean rebuild | `docker compose build --no-cache` |

### File Locations

| File | Purpose |
|------|---------|
| `config.yml.local` | Your configuration |
| `.env.docker` | Docker environment variables |
| `logs/` | Application logs |
| `data_exchange/` | Shared data between services |

## Conclusion

Following this guide ensures a successful installation of ThothAI on Windows. The key points are:

1. Use the provided scripts to handle Windows-specific issues
2. Always fix line endings before building Docker images
3. Keep your configuration files secure and never commit them
4. Use WSL or Git Bash for shell scripts
5. Monitor Docker resources and logs for issues

For production deployment, consider additional security measures and use a proper HTTPS reverse proxy.
