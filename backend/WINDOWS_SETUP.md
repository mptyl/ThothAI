# ThothAI Windows Setup Guide

## Prerequisites

1. **Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop/
   - Ensure WSL 2 backend is enabled (recommended)
   - After installation, start Docker Desktop

2. **Python 3.7+** (optional but recommended)
   - Download from: https://www.python.org
   - During installation, check "Add Python to PATH"

3. **Git for Windows**
   - Download from: https://git-scm.com/download/win
   - This also provides Git Bash if needed

## Installation Steps

### Step 1: Clone the Repository

Open Command Prompt or PowerShell and run:

```cmd
git clone https://github.com/mptyl/thoth.git
cd thoth
```

### Step 2: Configure Environment

Copy the environment template:
```cmd
copy _env.template _env
```

Edit `_env` file with a text editor (Notepad, VS Code, etc.) and add your API keys.

### Step 3: Setup Docker Environment

Run the setup script:

```cmd
setup-docker.bat
```

Or if the batch file doesn't work, use Python directly:
```cmd
python setup-docker.py
```

This script will:
- Create Docker network `thothnet`
- Create Docker volume `thoth-shared-data`
- Create necessary directories (logs, exports, etc.)
- Copy `dev_databases` to the Docker volume
- Copy `db.sqlite3` if it exists

### Step 4: Start ThothAI

Use the provided batch file:
```cmd
start-docker-windows.bat
```

Or manually run Docker Compose:
```cmd
docker-compose up --build
```

### Step 5: Access the Application

Open your browser and navigate to:
- Admin Interface: http://localhost:8040/admin
- API: http://localhost:8040/api

## Troubleshooting

### Issue: "docker" command not recognized

**Solution:** 
- Ensure Docker Desktop is installed and running
- Restart Command Prompt after Docker installation
- Check if Docker is in PATH: `where docker`

### Issue: "python" command not recognized

**Solution:**
- Install Python from https://www.python.org
- During installation, check "Add Python to PATH"
- Or use `py` instead of `python` on Windows

### Issue: Files not copied to Docker volume

**Solution:**
1. Ensure `data/dev_databases` directory exists
2. Check Docker volume exists: `docker volume ls`
3. Use the repair script to force copy:
   ```cmd
   fix-docker-volume.bat
   ```
   Or with Python:
   ```cmd
   python fix-docker-volume.py
   ```
4. If that doesn't work, manually copy files:
   ```cmd
   python setup-docker.py
   ```

### Issue: Permission denied errors

**Solution:**
- Run Command Prompt as Administrator
- Ensure Docker Desktop is running with proper permissions
- Check Windows Defender/Antivirus isn't blocking Docker

### Issue: Port 8040 already in use

**Solution:**
1. Check what's using the port:
   ```cmd
   netstat -an | findstr :8040
   ```
2. Either stop the conflicting service or change the port in `docker-compose.yml`

### Issue: Docker containers fail to start

**Solution:**
1. Check Docker Desktop is running
2. Ensure WSL 2 is properly configured
3. Check logs:
   ```cmd
   docker-compose logs app
   docker-compose logs qdrant
   ```

## Directory Structure After Setup

```
thoth/
├── data/
│   ├── dev_databases/      # Sample databases
│   └── db.sqlite3          # Django database
├── logs/                   # Application logs
├── exports/                # Exported data
├── setup_csv/              # CSV setup files
├── qdrant_storage/         # Vector database storage
├── _env                    # Environment configuration
├── docker-compose.yml      # Docker configuration
├── setup-docker.py         # Cross-platform setup script
├── setup-docker.bat        # Windows batch file
└── start-docker-windows.bat # Windows start script
```

## Important Notes

1. **Line Endings**: If you edit files on Windows, be careful with line endings. Git should handle this automatically, but if you have issues, configure Git:
   ```cmd
   git config --global core.autocrlf true
   ```

2. **Path Separators**: The Python script handles path conversion automatically. Use forward slashes (/) in Docker commands even on Windows.

3. **Docker Volume Location**: On Windows, Docker volumes are stored in WSL 2 filesystem or in Docker Desktop's VM, not directly accessible from Windows Explorer.

4. **Memory Settings**: If you experience performance issues, increase Docker Desktop's memory allocation:
   - Docker Desktop → Settings → Resources → Advanced
   - Increase Memory to at least 4GB

## Getting Help

If you encounter issues not covered here:
1. Check the full documentation at: https://mptyl.github.io/ThothDocs/
2. Check Docker Desktop logs: Docker Desktop → Troubleshoot → View Logs
3. Open an issue on GitHub: https://github.com/mptyl/thoth/issues