# Windows Installation Guide for ThothAI

This guide provides step-by-step instructions for installing ThothAI on Windows using Docker and WSL.

## Prerequisites

### 1. Install Required Software

#### Docker Desktop
1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. Install Docker Desktop with WSL 2 backend (recommended)
3. After installation, ensure Docker is running (you'll see the whale icon in the system tray)

#### Git for Windows
1. Download [Git for Windows](https://git-scm.com/download/win)
2. During installation, choose:
   - **Line ending conversions**: "Checkout as-is, commit Unix-style line endings"
   - This prevents issues with shell scripts in Docker containers

#### WSL 2 (Windows Subsystem for Linux)
1. Open PowerShell as Administrator and run:
   ```powershell
   wsl --install
   ```
2. Restart your computer if prompted
3. Set WSL 2 as default:
   ```powershell
   wsl --set-default-version 2
   ```

## Installation Steps

### Step 1: Clone the Repository

**Option A: Using PowerShell (Recommended for Windows)**
```powershell
cd C:\Projects  # or your preferred directory
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI
```

**Option B: Using WSL**
```bash
cd ~
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
.\install.ps1
```

The installer will:
- Validate your configuration
- Create necessary environment files
- Set up Docker networks and volumes
- Build and start all services

### Step 4: Prepare Docker Environment (For Subsequent Runs)

After the initial installation, for subsequent runs:

1. **Prepare the environment:**
   ```powershell
   .\scripts\prepare-docker-env.ps1
   ```

2. **Fix line endings (critical on Windows):**
   ```bash
   # In WSL or Git Bash
   ./scripts/prepare-docker-build.sh
   ```

### Step 5: Start the Services

```powershell
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

## Troubleshooting Common Windows Issues

### Issue 1: "No such file or directory" errors

**Cause**: Windows line endings (CRLF) in shell scripts

**Solution**:
```bash
# In WSL or Git Bash
./scripts/fix-line-endings.sh
docker-compose build --no-cache
```

### Issue 2: Missing files during Docker build

**Cause**: Files not synchronized to Git repository

**Solution**:
```bash
git pull
docker-compose build --no-cache
```

### Issue 3: Services stuck during startup

**Cause**: Shell scripts hanging due to line ending issues

**Solution**:
1. Check container logs:
   ```powershell
   .\scripts\check-docker-logs.ps1
   ```

2. Fix and rebuild:
   ```bash
   ./scripts/prepare-docker-build.sh
   docker-compose down
   docker-compose build --no-cache
   docker-compose up
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
- Password: `admin`

**⚠️ Important**: Change these credentials immediately after first login!

## Daily Usage

### Starting ThothAI

After initial installation, you can start ThothAI with:

```powershell
# Quick start (if environment is already prepared)
docker-compose up

# Full preparation and start (recommended)
.\scripts\prepare-docker-env.ps1
docker-compose up --build
```

### Stopping ThothAI

```powershell
# Stop services
docker-compose down

# Stop and remove volumes (careful - removes data!)
docker-compose down -v
```

### Updating ThothAI

```powershell
# Pull latest changes
git pull

# Prepare environment for Windows
.\scripts\prepare-docker-env.ps1

# In WSL/Git Bash - fix line endings
./scripts/prepare-docker-build.sh

# Rebuild and start
docker-compose build --no-cache
docker-compose up
```

## Best Practices for Windows

1. **Always use WSL or Git Bash** for running shell scripts
2. **Configure Git** to handle line endings correctly:
   ```bash
   git config --global core.autocrlf input
   ```

3. **Store the project in WSL filesystem** for better performance:
   - Clone to `\\wsl$\Ubuntu\home\username\projects\` instead of `C:\`
   - Access in Windows Explorer via `\\wsl$`

4. **Use PowerShell scripts** when provided (`.ps1` files)

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
   docker-compose build --no-cache
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
| First installation | `.\install.ps1` |
| Prepare environment | `.\scripts\prepare-docker-env.ps1` |
| Fix line endings | `./scripts/prepare-docker-build.sh` |
| Start services | `docker-compose up --build` |
| Stop services | `docker-compose down` |
| View logs | `.\scripts\check-docker-logs.ps1` |
| Rebuild everything | `docker-compose build --no-cache` |

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