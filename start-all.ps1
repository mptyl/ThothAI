# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

# Start all ThothAI services locally for PowerShell

param(
    [switch]$Detached
)

$ErrorActionPreference = "Continue"

# Paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Starting ThothAI Local Development Environment" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

# --- Configuration ---
$BACKEND_PORT = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8040" }
$FRONTEND_PORT = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "3040" }
$SQL_GENERATOR_PORT = if ($env:SQL_GENERATOR_PORT) { $env:SQL_GENERATOR_PORT } else { "8020" }
$QDRANT_PORT = if ($env:QDRANT_PORT) { $env:QDRANT_PORT } else { "6333" }
$QDRANT_LOCAL_STORAGE = "qdrant_storage_local"

# --- Load .env.local ---
if (Test-Path ".env.local") {
    Write-Host "Loading configuration from .env.local..."
    Get-Content ".env.local" | ForEach-Object {
        if ($_ -match "^(?<name>[^#\s=]+)=(?<value>.*)$") {
            $name = $Matches.name.Trim()
            $value = $Matches.value.Trim()
            if ($value -match "^'.*'$" -or $value -match '^".*"$') {
                $value = $value.Substring(1, $value.Length - 2)
            }
            [Environment]::SetEnvironmentVariable($name, $value)
        }
    }
} else {
    Write-Host "[WARN] .env.local not found. Creating from template..." -ForegroundColor Yellow
    if (Test-Path ".env.local.template") {
        Copy-Item ".env.local.template" ".env.local"
        Write-Host "Created .env.local - please configure API keys before running again." -ForegroundColor Red
        exit 1
    } else {
        Write-Host "[X] .env.local.template not found. Cannot continue." -ForegroundColor Red
        exit 1
    }
}

# --- Step 1: Reclaim Ports ---
Write-Host "`nStep 1: Reclaiming ports..." -ForegroundColor Blue
$ports = @($BACKEND_PORT, $FRONTEND_PORT, $SQL_GENERATOR_PORT, $QDRANT_PORT)
foreach ($port in $ports) {
    if ((Get-Command "netstat" -ErrorAction SilentlyContinue)) {
        $found = netstat -ano | Select-String ":$port\s+.*\s+LISTENING"
        if ($found) {
            foreach ($line in $found) {
                $pid = ($line.ToString() -split '\s+')[-1]
                if ($pid -and $pid -ne "0") {
                    Write-Host "  Port $port is occupied by PID $pid. Reclaiming..." -ForegroundColor Yellow
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }
}

# --- Step 2: Ensure Docker services ---
if ((Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "`nStep 2: Checking Docker services..." -ForegroundColor Blue
    
    # Ensure Mermaid
    if (-not (docker ps --format '{{.Names}}' | Select-String 'thoth-mermaid-service')) {
        Write-Host "  Starting Mermaid service..." -ForegroundColor Yellow
        docker compose up -d mermaid-service
    } else {
        Write-Host "  Mermaid service already running."
    }

    # Start local Qdrant
    Write-Host "`nStep 3: Starting Qdrant with local storage..." -ForegroundColor Blue
    if (-not (Test-Path $QDRANT_LOCAL_STORAGE)) { New-Item -ItemType Directory -Path $QDRANT_LOCAL_STORAGE | Out-Null }
    
    docker stop thoth-qdrant-local 2>$null | Out-Null
    docker rm thoth-qdrant-local 2>$null | Out-Null
    
    $fullStoragePath = Resolve-Path $QDRANT_LOCAL_STORAGE
    docker run -d `
        --name thoth-qdrant-local `
        -p "${QDRANT_PORT}:6333" `
        -v "${fullStoragePath}:/qdrant/storage" `
        qdrant/qdrant:latest | Out-Null
    
    Write-Host "  Qdrant started on port $QDRANT_PORT." -ForegroundColor Green

    # Wait for Qdrant
    Write-Host "  Waiting for Qdrant to be ready..." -ForegroundColor Yellow
    $ready = $false
    for ($i=0; $i -lt 30; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:$QDRANT_PORT/" -UseBasicParsing -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {}
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { Write-Host "  [!] Qdrant initialization timeout." -ForegroundColor Red }
} else {
    Write-Host "`n[X] Docker not found. Qdrant is MANDATORY." -ForegroundColor Red
    exit 1
}

# --- Step 4: Start Backend ---
Write-Host "`nStep 4: Starting Backend on port $BACKEND_PORT..." -ForegroundColor Blue
if (-not (Test-Path "backend/.venv")) {
    Write-Host "[X] Backend .venv not found. Run 'cd backend; uv sync'." -ForegroundColor Red
    exit 1
}

$BACKEND_PYTHON = "backend/.venv/Scripts/python.exe"
if (-not (Test-Path $BACKEND_PYTHON)) { $BACKEND_PYTHON = "backend/.venv/bin/python" } # Support Git Bash/cross-env

# Initialize DB (Python migrations)
& $BACKEND_PYTHON backend/manage.py migrate --run-syncdb | Out-Null
& $BACKEND_PYTHON backend/manage.py createcachetable 2>$null | Out-Null

$startBackend = {
    param($py, $port)
    Set-Location (Get-Location)
    & $py backend/manage.py runserver $port
}

if ($Detached) {
    Start-Job -ScriptBlock $startBackend -ArgumentList $BACKEND_PYTHON, $BACKEND_PORT -Name "Thoth-Backend" | Out-Null
} else {
    # In interactive mode, we start them as jobs but we'll wait for Ctrl+C
    Start-Job -ScriptBlock $startBackend -ArgumentList $BACKEND_PYTHON, $BACKEND_PORT -Name "Thoth-Backend" | Out-Null
}
Write-Host "  Backend started."

# --- Step 5: Start SQL Generator ---
Write-Host "`nStep 5: Starting SQL Generator on port $SQL_GENERATOR_PORT..." -ForegroundColor Blue
if (-not (Test-Path "frontend/sql_generator/.venv")) {
    Write-Host "[X] SQL Generator .venv not found. Run 'cd frontend/sql_generator; uv sync'." -ForegroundColor Red
    exit 1
}

$SQLGEN_VENV = "frontend/sql_generator/.venv"
$env:PORT = $SQL_GENERATOR_PORT
$env:DJANGO_SERVER = "http://localhost:$BACKEND_PORT"
$env:VECTOR_DB_HOST = "localhost"
$env:VECTOR_DB_PORT = $QDRANT_PORT

$startSqlGen = {
    param($port, $be, $vhost, $vport)
    $env:PORT = $port
    $env:DJANGO_SERVER = $be
    $env:VECTOR_DB_HOST = $vhost
    $env:VECTOR_DB_PORT = $vport
    Set-Location "frontend/sql_generator"
    uv run python main.py
}

Start-Job -ScriptBlock $startSqlGen -ArgumentList $SQL_GENERATOR_PORT, $env:DJANGO_SERVER, $env:VECTOR_DB_HOST, $env:VECTOR_DB_PORT -Name "Thoth-SqlGen" | Out-Null
Write-Host "  SQL Generator started."

# --- Step 6: Start Frontend ---
Write-Host "`nStep 6: Starting Frontend on port $FRONTEND_PORT..." -ForegroundColor Blue
$env:NEXT_PUBLIC_DJANGO_SERVER = "http://localhost:$BACKEND_PORT"
$env:NEXT_PUBLIC_SQL_GENERATOR_URL = "http://localhost:$SQL_GENERATOR_PORT"

$startFrontend = {
    param($port, $be, $sql)
    $env:PORT = $port
    $env:DJANGO_SERVER = $be
    $env:SQL_GENERATOR_URL = $sql
    $env:NEXT_PUBLIC_DJANGO_SERVER = $be
    $env:NEXT_PUBLIC_SQL_GENERATOR_URL = $sql
    Set-Location "frontend"
    npm run dev
}

Start-Job -ScriptBlock $startFrontend -ArgumentList $FRONTEND_PORT, $env:NEXT_PUBLIC_DJANGO_SERVER, $env:NEXT_PUBLIC_SQL_GENERATOR_URL -Name "Thoth-Frontend" | Out-Null
Write-Host "  Frontend started."

# --- Summary ---
Write-Host "`n================================================" -ForegroundColor Green
Write-Host "ThothAI Local Development Environment Started" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host "`nService URLs:"
Write-Host "  Frontend:      http://localhost:$FRONTEND_PORT"
Write-Host "  Backend:       http://localhost:$BACKEND_PORT"
Write-Host "  SQL Generator: http://localhost:$SQL_GENERATOR_PORT"
Write-Host "  Qdrant:        http://localhost:$QDRANT_PORT"

if ($Detached) {
    Write-Host "`nServices are running in the background as PowerShell Jobs." -ForegroundColor Green
    Write-Host "Use 'Get-Job' to see status and 'Stop-Job' or '.\stop-all.ps1' to stop them."
} else {
    Write-Host "`nPress Ctrl+C to stop all services (Running as jobs)..." -ForegroundColor Yellow
    try {
        while ($true) { Start-Sleep -Seconds 1 }
    }
    finally {
        & (Join-Path $ScriptDir "stop-all.ps1")
    }
}
