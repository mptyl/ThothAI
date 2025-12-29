# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Start all ThothAI services (PowerShell version)
# This script starts Frontend, Django backend, Qdrant, Mermaid Service, and SQL Generator services
# For local development: Django, SQL Generator, and Next.js run natively; Qdrant and Mermaid run in Docker

$ErrorActionPreference = "Stop"

# Configuration
$SqlGenDir = "frontend/sql_generator"
$ConfigFile = "config.yml.local"
$EnvFile = ".env.local"

# Global process tracking
$DjangoProcess = $null
$SqlGenProcess = $null
$MermaidContainer = $null
$FrontendProcess = $null
$QdrantContainer = $null

# Colors for output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Test-Port {
    param([int]$Port)
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
        return $null -ne $connection
    } catch {
        return $false
    }
}

function Kill-Port {
    param([int]$Port)
    $processes = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | 
                 Where-Object { $_.State -eq "Listen" } | 
                 Select-Object -ExpandProperty OwningProcess | 
                 Sort-Object -Unique
    if ($processes) {
        Write-ColorOutput "Killing processes on port $Port..." "Yellow"
        foreach ($pid_ in $processes) {
            Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue 2>$null
        }
        Start-Sleep -Seconds 2
        # Force kill if still running
        $remaining = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | 
                     Where-Object { $_.State -eq "Listen" } | 
                     Select-Object -ExpandProperty OwningProcess | 
                     Sort-Object -Unique
        if ($remaining) {
            Write-ColorOutput "Force killing remaining processes: $remaining" "Yellow"
            foreach ($pid_ in $remaining) {
                Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue 2>$null
            }
        }
    }
}

function Wait-ForPort {
    param(
        [int]$Port,
        [string]$ServiceName,
        [int]$MaxRetries = 30
    )
    Write-ColorOutput "Waiting for $ServiceName to start..." "Yellow"
    for ($i = 1; $i -le $MaxRetries; $i++) {
        if (Test-Port $Port) {
            Write-ColorOutput "✓ $ServiceName started successfully on port $Port" "Green"
            return $true
        }
        Start-Sleep -Seconds 1
    }
    Write-ColorOutput "Failed to start $ServiceName" "Red"
    return $false
}

function Cleanup-SqlGenerator {
    Write-ColorOutput "Cleaning up any existing SQL Generator processes..." "Yellow"
    Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
        $_.CommandLine -like "*main.py*" -or $_.CommandLine -like "*sql_generator*" 
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# --- Main ---

Write-ColorOutput "Starting ThothAI Services..." "Blue"
Write-ColorOutput "=============================" "Blue"

# Detect Python
$PythonBin = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } 
             elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } 
             else { Write-ColorOutput "Error: Python required"; exit 1 }

# Detach from any inherited virtual environment to prevent uv warnings
if ($env:VIRTUAL_ENV) {
    Write-ColorOutput "Detected active virtual environment at $env:VIRTUAL_ENV. Unsetting VIRTUAL_ENV for a clean start." "Yellow"
    Remove-Item Env:\VIRTUAL_ENV
}

# Config Check
if (-not (Test-Path $ConfigFile)) {
    Write-ColorOutput "Error: $ConfigFile not found in root directory" "Red"
    Write-ColorOutput "Please copy config.yml to $ConfigFile and update it with your settings" "Red"
    exit 1
}

# Generate .env.local
Write-ColorOutput "Generating $EnvFile from $ConfigFile..." "Cyan"
& $PythonBin scripts/generate_env_local.py
if ($LASTEXITCODE -ne 0) { 
    Write-ColorOutput "Failed to generate $EnvFile from $ConfigFile" "Red"
    exit 1 
}

# Force DEBUG=TRUE for local development (required for Django static file serving)
if (Test-Path $EnvFile) {
    $content = Get-Content $EnvFile -Raw
    if ($content -match "^DEBUG=") {
        $content = $content -replace "^DEBUG=.*", "DEBUG=TRUE"
    } else {
        $content += "`nDEBUG=TRUE"
    }
    $content | Set-Content $EnvFile -NoNewline
    Write-ColorOutput "Forced DEBUG=TRUE in $EnvFile for local development" "Yellow"
}

# Update Dependencies
Write-ColorOutput "Resolving local database dependencies..." "Cyan"
$DbDepOutput = & $PythonBin scripts/update_local_db_dependencies.py 2>&1
Write-Host $DbDepOutput

if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput "Failed to resolve database dependencies. Please review config.yml.local." "Red"
    exit 1
}

$SyncRequired = $DbDepOutput -match "SYNC_REQUIRED=true"
$SyncBackend = $DbDepOutput -match "SYNC_BACKEND=true"
$SyncSqlGen = $DbDepOutput -match "SYNC_SQL_GENERATOR=true"

if ($SyncRequired) {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-ColorOutput "Error: 'uv' is required to install database dependencies. Install it from https://docs.astral.sh/uv/getting-started/." "Red"
        exit 1
    }
}

if ($SyncBackend) {
    Write-ColorOutput "Synchronizing backend dependencies (uv lock --refresh && uv sync)..." "Cyan"
    
    # Configure MariaDB Connector/C path for Windows
    $MariaDBConfigPath = $null
    
    # Check environment variable first
    if ($env:MARIADB_CONFIG_PATH -and (Test-Path $env:MARIADB_CONFIG_PATH)) {
        $MariaDBConfigPath = $env:MARIADB_CONFIG_PATH
        Write-ColorOutput "Detected MariaDB Connector/C at: $MariaDBConfigPath (Environment Variable)" "Cyan"
    } else {
        # Check standard Windows installation paths
        $possiblePaths = @(
            "${env:ProgramFiles}\MariaDB\MariaDB Connector C 64-bit\bin",
            "${env:ProgramFiles(x86)}\MariaDB\MariaDB Connector C\bin",
            "C:\Program Files\MariaDB\MariaDB Connector C 64-bit\bin",
            "C:\Program Files (x86)\MariaDB\MariaDB Connector C\bin"
        )
        
        foreach ($path in $possiblePaths) {
            if (Test-Path "$path\mariadb_config.exe") {
                $MariaDBConfigPath = $path
                Write-ColorOutput "Detected MariaDB Connector/C at: $MariaDBConfigPath (Standard Path)" "Cyan"
                break
            }
        }
    }
    
    Push-Location backend
    try {
        # Add MariaDB to PATH if found
        if ($MariaDBConfigPath) {
            $env:PATH = "$MariaDBConfigPath;$env:PATH"
        }
        
        uv lock --refresh
        if ($LASTEXITCODE -ne 0) { throw "uv lock --refresh failed" }
        uv sync
        if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }
    } catch {
        Write-ColorOutput "Failed to synchronize backend dependencies. Check the output above." "Red"
        Pop-Location
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-ColorOutput "Backend dependencies already up to date." "Green"
}

if ($SyncSqlGen) {
    Write-ColorOutput "Synchronizing SQL Generator dependencies (uv lock --refresh && uv sync)..." "Cyan"
    
    # Configure MariaDB Connector/C path for Windows
    $MariaDBConfigPath = $null
    
    # Check environment variable first
    if ($env:MARIADB_CONFIG_PATH -and (Test-Path $env:MARIADB_CONFIG_PATH)) {
        $MariaDBConfigPath = $env:MARIADB_CONFIG_PATH
        Write-ColorOutput "Detected MariaDB Connector/C at: $MariaDBConfigPath (Environment Variable)" "Cyan"
    } else {
        # Check standard Windows installation paths
        $possiblePaths = @(
            "${env:ProgramFiles}\MariaDB\MariaDB Connector C 64-bit\bin",
            "${env:ProgramFiles(x86)}\MariaDB\MariaDB Connector C\bin",
            "C:\Program Files\MariaDB\MariaDB Connector C 64-bit\bin",
            "C:\Program Files (x86)\MariaDB\MariaDB Connector C\bin"
        )
        
        foreach ($path in $possiblePaths) {
            if (Test-Path "$path\mariadb_config.exe") {
                $MariaDBConfigPath = $path
                Write-ColorOutput "Detected MariaDB Connector/C at: $MariaDBConfigPath (Standard Path)" "Cyan"
                break
            }
        }
    }
    
    Push-Location frontend/sql_generator
    try {
        # Add MariaDB to PATH if found
        if ($MariaDBConfigPath) {
            $env:PATH = "$MariaDBConfigPath;$env:PATH"
        }
        
        uv lock --refresh
        if ($LASTEXITCODE -ne 0) { throw "uv lock --refresh failed" }
        uv sync
        if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }
    } catch {
        Write-ColorOutput "Failed to synchronize SQL Generator dependencies. Check the output above." "Red"
        Pop-Location
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-ColorOutput "SQL Generator dependencies already up to date." "Green"
}

# Load Env Vars
if (Test-Path $EnvFile) {
    Write-ColorOutput "Loading environment from $EnvFile" "Cyan"
    Get-Content $EnvFile | Where-Object { $_ -match "^[^#].*=" } | ForEach-Object {
        $name, $value = $_.Split('=', 2)
        if ($name.Trim() -ne "PORT") {
            Set-Item -Path "Env:\$($name.Trim())" -Value $value.Trim()
        }
    }
    # Avoid leaking a generic PORT that could clash with service-specific ports
    Remove-Item Env:\PORT -ErrorAction SilentlyContinue
} else {
    Write-ColorOutput "Error: $EnvFile not found in root directory" "Red"
    Write-ColorOutput "Please ensure scripts/generate_env_local.py succeeds" "Red"
    exit 1
}

# Validate Backend AI
Write-ColorOutput "Validating backend AI provider/model from .env.local..." "Cyan"
& $PythonBin scripts/validate_backend_ai.py --from-env
if ($LASTEXITCODE -ne 0) { 
    Write-ColorOutput "Backend AI validation failed. Check BACKEND_AI_PROVIDER, BACKEND_AI_MODEL and API keys in .env.local." "Red"
    exit 1 
}

# Port configuration from environment
$BackendPort = if ($env:BACKEND_PORT) { [int]$env:BACKEND_PORT } else { 8200 }
$FrontendPort = if ($env:FRONTEND_PORT) { [int]$env:FRONTEND_PORT } else { 3200 }
$SqlGenPort = if ($env:SQL_GENERATOR_PORT) { [int]$env:SQL_GENERATOR_PORT } else { 8180 }
$MermaidPort = if ($env:MERMAID_SERVICE_PORT) { [int]$env:MERMAID_SERVICE_PORT } else { 8003 }
$QdrantPort = 6334

if (-not $env:MERMAID_SERVICE_URL) {
    $env:MERMAID_SERVICE_URL = "http://localhost:$MermaidPort"
}

# --- Services Start ---

# 1. Django Backend
Write-ColorOutput "`nStep 1: Starting all services..." "Blue"

if (Test-Port $BackendPort) {
    Write-ColorOutput "✓ Django backend is already running on port $BackendPort" "Green"
} else {
    Write-ColorOutput "Django backend is NOT running on port $BackendPort" "Yellow"
    Write-ColorOutput "Starting Django backend..." "Yellow"
    
    if (Test-Path "backend") {
        Push-Location backend
        try {
            if (Get-Command uv -ErrorAction SilentlyContinue) {
                Write-ColorOutput "Starting Django with uv..." "Green"
                # Django will use environment variables already exported from root .env.local
                # Unset VIRTUAL_ENV to avoid conflicts with uv's environment detection
                $env:VIRTUAL_ENV = $null
                $DjangoProcess = Start-Process -FilePath "uv" -ArgumentList "run", "python", "manage.py", "runserver", $BackendPort -PassThru -NoNewWindow
            } else {
                Write-ColorOutput "Starting Django with python..." "Yellow"
                $DjangoProcess = Start-Process -FilePath "python" -ArgumentList "manage.py", "runserver", $BackendPort -PassThru -NoNewWindow
            }
        } finally {
            Pop-Location
        }
        
        if (-not (Wait-ForPort -Port $BackendPort -ServiceName "Django backend")) {
            Write-ColorOutput "Failed to start Django backend" "Red"
            exit 1
        }
    } else {
        Write-ColorOutput "Backend directory not found!" "Red"
        exit 1
    }
}

# 2. Qdrant (Docker)
if (Test-Port $QdrantPort) {
    Write-ColorOutput "✓ Qdrant is already running on port $QdrantPort" "Green"
} else {
    Write-ColorOutput "Qdrant is NOT running on port $QdrantPort" "Yellow"
    
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-ColorOutput "Docker is not installed or not available" "Red"
        Write-ColorOutput "Please install Docker to run Qdrant" "Yellow"
        exit 1
    }
    
    Write-ColorOutput "Starting Qdrant Container..." "Yellow"
    if (docker ps -a --format "{{.Names}}" | Select-String "qdrant-thoth") {
        Write-ColorOutput "Starting existing qdrant-thoth container..." "Yellow"
        docker start qdrant-thoth | Out-Null
        # Ensure it auto-starts with Docker daemon
        docker update --restart unless-stopped qdrant-thoth | Out-Null
        $QdrantContainer = "qdrant-thoth"
    } else {
        Write-ColorOutput "Creating and starting new qdrant-thoth container..." "Yellow"
        $currentDir = (Get-Location).Path
        docker run -d --name qdrant-thoth --restart unless-stopped -p "${QdrantPort}:6333" -v "${currentDir}/qdrant_storage:/qdrant/storage:z" qdrant/qdrant | Out-Null
        $QdrantContainer = "qdrant-thoth"
    }
    
    if (-not (Wait-ForPort -Port $QdrantPort -ServiceName "Qdrant")) {
        Write-ColorOutput "Failed to start Qdrant" "Red"
        exit 1
    }
}

# 3. SQL Generator
Write-ColorOutput "Checking SQL Generator on port $SqlGenPort..." "Yellow"

# Always cleanup existing SQL Generator processes first
Cleanup-SqlGenerator

if (Test-Port $SqlGenPort) {
    Write-ColorOutput "Port $SqlGenPort still in use, killing processes..." "Yellow"
    Kill-Port $SqlGenPort
}

Write-ColorOutput "Starting SQL Generator..." "Yellow"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-ColorOutput "Error: 'uv' is required to run the SQL Generator locally." "Red"
    Write-ColorOutput "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh" "Yellow"
    exit 1
}

Push-Location $SqlGenDir
try {
    # Check if virtual environment exists
    if (-not (Test-Path ".venv")) {
        Write-ColorOutput "Creating virtual environment for SQL Generator..." "Yellow"
        $env:VIRTUAL_ENV = $null
        uv sync --frozen
        if ($LASTEXITCODE -ne 0) { throw "uv sync --frozen failed" }
    } else {
        Write-ColorOutput "Updating SQL Generator dependencies..." "Yellow"
        $env:VIRTUAL_ENV = $null
        uv sync --frozen
        if ($LASTEXITCODE -ne 0) { throw "uv sync --frozen failed" }
    }
    
    # Start SQL Generator
    $env:PORT = $SqlGenPort
    $env:VIRTUAL_ENV = $null
    $SqlGenProcess = Start-Process -FilePath "uv" -ArgumentList "run", "python", "main.py" -PassThru -NoNewWindow
} catch {
    Write-ColorOutput "Failed to prepare SQL Generator environment: $_" "Red"
    Pop-Location
    exit 1
} finally {
    Pop-Location
}

if (-not (Wait-ForPort -Port $SqlGenPort -ServiceName "SQL Generator")) {
    Write-ColorOutput "Failed to start SQL Generator" "Red"
    exit 1
}

# 4. Mermaid Service (via Docker)
Write-ColorOutput "Checking Mermaid Service on port $MermaidPort..." "Yellow"

if (Test-Port $MermaidPort) {
    Write-ColorOutput "✓ Mermaid Service is already running on port $MermaidPort" "Green"
} else {
    Write-ColorOutput "Mermaid Service is NOT running on port $MermaidPort" "Yellow"
    
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-ColorOutput "Docker is not installed or not available" "Red"
        Write-ColorOutput "Please install Docker to run Mermaid Service" "Yellow"
        exit 1
    }
    
    Write-ColorOutput "Starting Mermaid Service via Docker..." "Yellow"
    
    if (Test-Path "docker/mermaid-service") {
        # Check if mermaid-thoth image exists
        $imageExists = docker images --format "{{.Repository}}" | Select-String "^mermaid-thoth$"
        if ($imageExists) {
            Write-ColorOutput "✓ Mermaid Service Docker image already exists" "Green"
        } else {
            Write-ColorOutput "Building Mermaid Service Docker image..." "Yellow"
            docker build -t mermaid-thoth docker/mermaid-service 2>&1 | Write-Host
            if ($LASTEXITCODE -ne 0) {
                Write-ColorOutput "Failed to build Mermaid Service Docker image" "Red"
                exit 1
            }
            Write-ColorOutput "✓ Mermaid Service Docker image built successfully" "Green"
        }
        
        # Check if mermaid-thoth container exists
        $containerExists = docker ps -a --format "{{.Names}}" | Select-String "^mermaid-thoth$"
        if ($containerExists) {
            Write-ColorOutput "Removing existing mermaid-thoth container..." "Yellow"
            docker rm -f mermaid-thoth | Out-Null
        }
        
        # Start Mermaid Service container
        docker run -d --name mermaid-thoth --restart unless-stopped -p "${MermaidPort}:8001" mermaid-thoth | Out-Null
        $MermaidContainer = "mermaid-thoth"
        
        if (-not (Wait-ForPort -Port $MermaidPort -ServiceName "Mermaid Service")) {
            Write-ColorOutput "Failed to start Mermaid Service" "Red"
            exit 1
        }
    } else {
        Write-ColorOutput "Mermaid Service directory not found!" "Red"
        exit 1
    }
}

# 5. Frontend (Next.js)
Write-ColorOutput "Checking Frontend on port $FrontendPort..." "Yellow"
if (Test-Port $FrontendPort) {
    Write-ColorOutput "✓ Frontend is already running on port $FrontendPort" "Green"
} else {
    Write-ColorOutput "Frontend is NOT running on port $FrontendPort" "Yellow"
    Write-ColorOutput "Starting Frontend..." "Yellow"
    
    if (Test-Path "frontend") {
        Push-Location frontend
        try {
            # Check if node_modules exists
            if (-not (Test-Path "node_modules")) {
                # Ensure Node.js/npm is installed
                if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
                    Write-ColorOutput "Error: npm is not installed. Please install Node.js (v20+) and retry." "Red"
                    exit 1
                }
                Write-ColorOutput "Installing Frontend dependencies..." "Yellow"
                npm install
                if ($LASTEXITCODE -ne 0) {
                    Write-ColorOutput "Failed to install Frontend dependencies" "Red"
                    exit 1
                }
            }
            
            # Start Frontend with specific port
            $env:PORT = $FrontendPort
            $FrontendProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -PassThru -NoNewWindow
        } finally {
            Pop-Location
        }
        
        if (-not (Wait-ForPort -Port $FrontendPort -ServiceName "Frontend")) {
            Write-ColorOutput "Failed to start Frontend" "Red"
            exit 1
        }
    } else {
        Write-ColorOutput "Frontend directory not found!" "Red"
        exit 1
    }
}

# Display service information
Write-ColorOutput "`nAll services started successfully!" "Green"
Write-ColorOutput "===========================================" "Blue"
Write-ColorOutput "Service URLs:" "Blue"
Write-ColorOutput "   Frontend App:     http://localhost:$FrontendPort" "Green"
Write-ColorOutput "   Backend Home:     http://localhost:$BackendPort" "Green"
Write-ColorOutput "   Django Admin:     http://localhost:$BackendPort/admin" "Green"
Write-ColorOutput "   SQL Generator:    http://localhost:$SqlGenPort" "Green"
Write-ColorOutput "   API Docs:         http://localhost:$SqlGenPort/docs" "Green"
Write-ColorOutput "   Mermaid Service:  http://localhost:$MermaidPort" "Green"
Write-ColorOutput "   Qdrant API:       http://localhost:$QdrantPort" "Green"

# Function to handle cleanup
function Cleanup {
    Write-ColorOutput "`nStopping services..." "Yellow"
    
    # Stop Frontend
    if ($FrontendProcess -and -not $FrontendProcess.HasExited) {
        Stop-Process -Id $FrontendProcess.Id -Force -ErrorAction SilentlyContinue
        Write-ColorOutput "✓ Frontend stopped" "Green"
    }
    
    # Stop SQL Generator
    if ($SqlGenProcess -and -not $SqlGenProcess.HasExited) {
        Stop-Process -Id $SqlGenProcess.Id -Force -ErrorAction SilentlyContinue
        Write-ColorOutput "✓ SQL Generator stopped" "Green"
    }
    
    # Stop Django if we started it
    if ($DjangoProcess -and -not $DjangoProcess.HasExited) {
        Write-ColorOutput "Stopping Django backend..." "Yellow"
        Stop-Process -Id $DjangoProcess.Id -Force -ErrorAction SilentlyContinue
        Write-ColorOutput "✓ Django backend stopped" "Green"
    }
    
    # Ask about Mermaid container
    if ($MermaidContainer) {
        $ans = Read-Host "Stop Mermaid container? (y/N)"
        if ($ans -match "^[Yy]") {
            docker stop $MermaidContainer | Out-Null
            docker rm $MermaidContainer | Out-Null
            Write-ColorOutput "✓ Mermaid container stopped and removed" "Green"
        } else {
            Write-ColorOutput "Mermaid container left running" "Yellow"
        }
    }
    
    # Ask about Qdrant container
    if ($QdrantContainer) {
        $ans = Read-Host "Stop Qdrant container? (y/N)"
        if ($ans -match "^[Yy]") {
            docker stop $QdrantContainer | Out-Null
            Write-ColorOutput "✓ Qdrant container stopped" "Green"
        } else {
            Write-ColorOutput "Qdrant container left running" "Yellow"
        }
    }
    
    Write-ColorOutput "All services stopped" "Green"
    exit 0
}

# Set up trap to catch Ctrl+C
$originalErrorActionPreference = $ErrorActionPreference
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Cleanup
}

# Handle Ctrl+C more gracefully
try {
    [Console]::TreatControlCAsInput = $false
} catch {
    # Ignore if not running in console
}

Write-ColorOutput "`n===========================================" "Blue"
Write-ColorOutput "All services are running. Press Ctrl+C to stop all services." "Green"
Write-ColorOutput "===========================================" "Blue"

# Wait for services (keep script running)
try {
    while ($true) {
        Start-Sleep -Seconds 1
        
        # Check if any process has exited unexpectedly
        if ($DjangoProcess -and $DjangoProcess.HasExited) {
            Write-ColorOutput "Django backend has stopped unexpectedly!" "Red"
            Cleanup
        }
        if ($SqlGenProcess -and $SqlGenProcess.HasExited) {
            Write-ColorOutput "SQL Generator has stopped unexpectedly!" "Red"
            Cleanup
        }
        if ($FrontendProcess -and $FrontendProcess.HasExited) {
            Write-ColorOutput "Frontend has stopped unexpectedly!" "Red"
            Cleanup
        }
    }
} catch [System.Management.Automation.PipelineStoppedException] {
    # Ctrl+C was pressed
    Cleanup
} catch {
    Write-ColorOutput "An error occurred: $_" "Red"
    Cleanup
}
