# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Start all ThothAI services (PowerShell version)

$ErrorActionPreference = "Stop"

# Configuration
$SqlGenDir = "frontend/sql_generator"
$ConfigFile = "config.yml.local"
$EnvFile = ".env.local"

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
    if (Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue) {
        return $true
    }
    return $false
}

function Kill-Port {
    param([int]$Port)
    $processes = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique
    if ($processes) {
        Write-ColorOutput "Killing processes on port $Port..." "Yellow"
        foreach ($pid_ in $processes) {
            Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue 2>$null
        }
    }
}

# --- Main ---

Write-ColorOutput "Starting ThothAI Services..." "Blue"
Write-ColorOutput "=============================" "Blue"

# Detect Python
$PythonBin = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } 
             elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } 
             else { Write-ColorOutput "Error: Python required"; exit 1 }

# Clean Env
if ($env:VIRTUAL_ENV) {
    Write-ColorOutput "Unsetting VIRTUAL_ENV..." "Yellow"
    Remove-Item Env:\VIRTUAL_ENV
}

# Config Check
if (-not (Test-Path $ConfigFile)) {
    Write-ColorOutput "Error: $ConfigFile not found" "Red"
    exit 1
}

# Generate .env.local
Write-ColorOutput "Generating $EnvFile from $ConfigFile..." "Cyan"
& $PythonBin scripts/generate_env_local.py
if ($LASTEXITCODE -ne 0) { exit 1 }

# Force DEBUG=TRUE
$content = Get-Content $EnvFile
if ($content -match "^DEBUG=") {
    $content = $content -replace "^DEBUG=.*", "DEBUG=TRUE"
} else {
    $content += "DEBUG=TRUE"
}
$content | Set-Content $EnvFile

# Update Dependencies
Write-ColorOutput "Resolving local database dependencies..." "Cyan"
$DbDepOutput = & $PythonBin scripts/update_local_db_dependencies.py
Write-Host $DbDepOutput

# Sync dependencies if needed
if ($DbDepOutput -match "SYNC_BACKEND=true") {
    Write-ColorOutput "Syncing backend..." "Cyan"
    Push-Location backend
    try { uv lock --refresh; uv sync } finally { Pop-Location }
}
if ($DbDepOutput -match "SYNC_SQL_GENERATOR=true") {
    Write-ColorOutput "Syncing SQL Generator..." "Cyan"
    Push-Location frontend/sql_generator
    try { uv lock --refresh; uv sync } finally { Pop-Location }
}

# Load Env Vars
Get-Content $EnvFile | Where-Object { $_ -match "^[^#].*=" } | ForEach-Object {
    $name, $value = $_.Split('=', 2)
    Set-Item -Path Env:\$name.Trim() -Value $value.Trim()
}

# Validate Backend AI
& $PythonBin scripts/validate_backend_ai.py --from-env
if ($LASTEXITCODE -ne 0) { exit 1 }

# Ports
$BackendPort = $env:BACKEND_PORT -as [int]
if (-not $BackendPort) { $BackendPort = 8200 }
$FrontendPort = $env:FRONTEND_PORT -as [int]
if (-not $FrontendPort) { $FrontendPort = 3200 }
$SqlGenPort = $env:SQL_GENERATOR_PORT -as [int]
if (-not $SqlGenPort) { $SqlGenPort = 8180 }
$MermaidPort = $env:MERMAID_SERVICE_PORT -as [int]
if (-not $MermaidPort) { $MermaidPort = 8003 }
$QdrantPort = 6334

# --- Services Start ---

# 1. Django Backend
if (Test-Port $BackendPort) {
    Write-ColorOutput "Django already running on $BackendPort" "Green"
} else {
    Write-ColorOutput "Starting Django Backend..." "Yellow"
    Push-Location backend
    try {
        if (Get-Command uv -ErrorAction SilentlyContinue) {
             # Start-Process is asynchronous by default on Windows
            $djangoProcess = Start-Process -FilePath "uv" -ArgumentList "run", "python", "manage.py", "runserver", $BackendPort -PassThru -NoNewWindow
        } else {
            # Fallback (venv assumed active or available)
             $djangoProcess = Start-Process -FilePath "python" -ArgumentList "manage.py", "runserver", $BackendPort -PassThru -NoNewWindow
        }
    } finally { Pop-Location }
}

# 2. Qdrant (Docker)
if (Test-Port $QdrantPort) {
    Write-ColorOutput "Qdrant already running on $QdrantPort" "Green"
} else {
    Write-ColorOutput "Starting Qdrant Container..." "Yellow"
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-ColorOutput "Docker not found. Skipping Qdrant." "Red"
    } else {
        if (docker ps -a --format "{{.Names}}" | Select-String "qdrant-thoth") {
            docker start qdrant-thoth | Out-Null
        } else {
             docker run -d --name qdrant-thoth --restart unless-stopped -p "${QdrantPort}:6333" -v "${PWD}/qdrant_storage:/qdrant/storage:z" qdrant/qdrant | Out-Null
        }
        
        # Wait for Qdrant
        $retries = 30
        while ($retries -gt 0) {
            if (Test-Port $QdrantPort) { break }
            Start-Sleep -Seconds 1
            $retries--
        }
        if (Test-Port $QdrantPort) { Write-ColorOutput "Qdrant started" "Green" } else { Write-ColorOutput "Qdrant failed to start" "Red" }
    }
}

# 3. SQL Generator
Kill-Port $SqlGenPort
Write-ColorOutput "Starting SQL Generator..." "Yellow"
Push-Location $SqlGenDir
try {
   $sqlGenProcess = Start-Process -FilePath "uv" -ArgumentList "run", "python", "main.py" -Environment @{ PORT=$SqlGenPort } -PassThru -NoNewWindow
} finally { Pop-Location }

# 4. Mermaid Service (Docker/Node)
# Prefer running as docker service if local node is not preferred, matching install.sh implies docker usually, 
# but start-all.sh runs it via npm start in docker/mermaid-service.
if (Test-Port $MermaidPort) {
    Write-ColorOutput "Mermaid Service already running on $MermaidPort" "Green"
} else {
    Write-ColorOutput "Starting Mermaid Service..." "Yellow"
    if (Test-Path "docker/mermaid-service") {
        Push-Location "docker/mermaid-service"
        try {
            if (-not (Test-Path "node_modules")) { npm install }
            $mermaidProcess = Start-Process -FilePath "npm" -ArgumentList "start" -Environment @{ PORT=$MermaidPort } -PassThru -NoNewWindow
        } finally { Pop-Location }
    }
}

# 5. Frontend
if (Test-Port $FrontendPort) {
    Write-ColorOutput "Frontend already running on $FrontendPort" "Green"
} else {
    Write-ColorOutput "Starting Frontend..." "Yellow"
    Push-Location frontend
    try {
        if (-not (Test-Path "node_modules")) { npm install }
        $frontendProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -Environment @{ PORT=$FrontendPort } -PassThru -NoNewWindow
    } finally { Pop-Location }
}

Write-ColorOutput "All services started!" "Green"
Write-ColorOutput "Frontend: http://localhost:$FrontendPort" "Cyan"
Write-ColorOutput "Backend:  http://localhost:$BackendPort" "Cyan"
Write-ColorOutput "SQL Gen:  http://localhost:$SqlGenPort" "Cyan"
Write-ColorOutput "Mermaid:  http://localhost:$MermaidPort" "Cyan"
Write-ColorOutput "Qdrant:   http://localhost:$QdrantPort" "Cyan"

Write-ColorOutput "Press Ctrl+C to stop..." "Yellow"
try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Write-ColorOutput "Stopping services..." "Yellow"
    if ($djangoProcess) { Stop-Process -Id $djangoProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($sqlGenProcess) { Stop-Process -Id $sqlGenProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($mermaidProcess) { Stop-Process -Id $mermaidProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($frontendProcess) { Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue }
    
    $ans = Read-Host "Stop Qdrant container? (y/N)"
    if ($ans -match "^[Yy]") { docker stop qdrant-thoth }
}
