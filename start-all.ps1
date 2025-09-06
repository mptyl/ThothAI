# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Start all ThothAI services
# This script starts Frontend, Django backend, Qdrant, and SQL Generator services

param(
    [string]$Mode = "local"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Global:Colors = @{
    Red = "Red"
    Green = "Green"  
    Yellow = "Yellow"
    Blue = "Blue"
    White = "White"
}

# Function to print colored output
function Write-Color {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Global:Colors[$Color]
}

# Global variables for cleanup
$Global:ProcessIds = @{}
$Global:QdrantContainer = ""

Write-Host "Starting ThothAI Services..." 
Write-Host "============================="

# Configuration
$SqlGenDir = "frontend/sql_generator"

# Load environment variables from root .env.local
if (Test-Path ".env.local") {
    Write-Color "Loading environment from .env.local" "White"
    
    # Read .env.local and set environment variables
    Get-Content ".env.local" | ForEach-Object {
        if ($_ -match '^([^#][^=]*)\s*=\s*(.*)$') {
            $name = $Matches[1].Trim()
            $value = $Matches[2].Trim()
            # Remove quotes if present
            $value = $value -replace '^[''"]|[''"]$', ''
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
    # Avoid leaking a generic PORT that could clash with service-specific ports
    [System.Environment]::SetEnvironmentVariable("PORT", $null, "Process")
}
else {
    Write-Color "Error: .env.local not found in root directory" "Red"
    
    # Try to create from template  
    if (Test-Path ".env.local.template") {
        Write-Color "Creating .env.local from .env.local.template..." "Yellow"
        Copy-Item ".env.local.template" ".env.local"
        Write-Color "✓ .env.local created successfully" "Green"
        Write-Host ""
        Write-Color "IMPORTANT: Please edit .env.local and add your API keys:" "Yellow"
        Write-Color "  - At least one AI provider (OpenAI, Anthropic, Gemini, etc.)" "White"
        Write-Color "  - DJANGO_API_KEY (change from default)" "White"
        Write-Color "  - Other configuration as needed" "White"
        Write-Host ""
        Write-Color "After editing .env.local, run ./start-all.ps1 again" "Yellow"
        exit 0
    }
    else {
        Write-Color "Template file .env.local.template not found" "Red"
        Write-Color "Please create .env.local manually or restore .env.local.template" "Red"
        exit 1
    }
}

# Port configuration from environment
$FrontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { 3200 }
$SqlGeneratorPort = if ($env:SQL_GENERATOR_PORT) { $env:SQL_GENERATOR_PORT } else { 8180 }
$BackendPort = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { 8200 }
$QdrantPort = 6334

# Function to check if a port is in use
function Test-Port {
    param([int]$Port)
    try {
        $listener = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
        return ($listener | Where-Object { $_.Port -eq $Port }) -ne $null
    }
    catch {
        return $false
    }
}

# Function to kill processes on a specific port
function Stop-ProcessOnPort {
    param([int]$Port)
    try {
        $processes = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | 
                    Select-Object -ExpandProperty OwningProcess -Unique
        
        if ($processes) {
            Write-Color "Killing processes on port $Port`: $($processes -join ', ')" "Yellow"
            $processes | ForEach-Object {
                try {
                    Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
                }
                catch {
                    # Ignore errors when stopping processes
                }
            }
            Start-Sleep -Seconds 2
        }
    }
    catch {
        # Port might not be in use
    }
}

# Function to cleanup SQL Generator processes
function Stop-SqlGeneratorProcesses {
    Write-Color "Cleaning up any existing SQL Generator processes..." "Yellow"
    
    try {
        Get-Process | Where-Object { 
            $_.ProcessName -like "*python*" -and 
            $_.CommandLine -like "*main.py*" 
        } | Stop-Process -Force -ErrorAction SilentlyContinue
        
        Get-Process | Where-Object { 
            $_.ProcessName -like "*python*" -and 
            $_.CommandLine -like "*sql_generator*" 
        } | Stop-Process -Force -ErrorAction SilentlyContinue
    }
    catch {
        # Ignore errors
    }
    
    Start-Sleep -Seconds 1
}

# Main script starts here
Write-Color "ThothAI Service Startup Script" "Blue"
Write-Host "==============================="

# Step 1: Check and start all required services
Write-Host ""
Write-Color "Step 1: Starting all services..." "Yellow"

# Check and start Django backend
if (Test-Port $BackendPort) {
    Write-Color "✓ Django backend is already running on port $BackendPort" "Green"
}
else {
    Write-Color "Django backend is NOT running on port $BackendPort" "Yellow"
    Write-Color "Starting Django backend..." "Yellow"
    
    # Check if backend directory exists
    if (Test-Path "backend") {
        Push-Location "backend"
        
        # Check if virtual environment exists
        if (Test-Path ".venv") {
            # Use uv to run Django if available
            if (Get-Command "uv" -ErrorAction SilentlyContinue) {
                Write-Color "Starting Django with uv..." "Green"
                # Remove VIRTUAL_ENV to avoid conflicts
                $oldVirtualEnv = $env:VIRTUAL_ENV
                $env:VIRTUAL_ENV = $null
                $process = Start-Process -FilePath "uv" -ArgumentList "run", "python", "manage.py", "runserver", $BackendPort -PassThru -WindowStyle Hidden
                $env:VIRTUAL_ENV = $oldVirtualEnv
                $Global:ProcessIds["Django"] = $process.Id
            }
            else {
                # Fallback to regular Python
                Write-Color "Starting Django with Python..." "Green"
                if (Test-Path ".venv/Scripts/activate.ps1") {
                    & .venv/Scripts/activate.ps1
                }
                elseif (Test-Path ".venv/bin/activate") {
                    # This won't work in PowerShell, but let's try
                    Write-Color "Warning: Unix-style venv detected, this may not work properly" "Yellow"
                }
                $process = Start-Process -FilePath "python" -ArgumentList "manage.py", "runserver", $BackendPort -PassThru -WindowStyle Hidden
                $Global:ProcessIds["Django"] = $process.Id
            }
        }
        else {
            Write-Color "Creating virtual environment for Django backend..." "Yellow"
            if (Get-Command "uv" -ErrorAction SilentlyContinue) {
                & uv sync
                $env:VIRTUAL_ENV = $null
                $process = Start-Process -FilePath "uv" -ArgumentList "run", "python", "manage.py", "runserver", $BackendPort -PassThru -WindowStyle Hidden
                $Global:ProcessIds["Django"] = $process.Id
            }
            else {
                & python -m venv .venv
                & .venv/Scripts/activate.ps1
                & pip install -r requirements.txt
                $process = Start-Process -FilePath "python" -ArgumentList "manage.py", "runserver", $BackendPort -PassThru -WindowStyle Hidden
                $Global:ProcessIds["Django"] = $process.Id
            }
        }
        
        Pop-Location
        
        # Wait for Django to start
        Write-Color "Waiting for Django to start..." "Yellow"
        $attempts = 30
        for ($i = 1; $i -le $attempts; $i++) {
            if (Test-Port $BackendPort) {
                Write-Color "✓ Django backend started successfully on port $BackendPort" "Green"
                break
            }
            Start-Sleep -Seconds 1
        }
        
        if (-not (Test-Port $BackendPort)) {
            Write-Color "Failed to start Django backend" "Red"
            exit 1
        }
    }
    else {
        Write-Color "Backend directory not found!" "Red"
        exit 1
    }
}

# Check and start Qdrant
if (Test-Port $QdrantPort) {
    Write-Color "✓ Qdrant is already running on port $QdrantPort" "Green"
}
else {
    Write-Color "Qdrant is NOT running on port $QdrantPort" "Yellow"
    
    # Check if Docker is available
    if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
        Write-Color "Docker is not installed or not available" "Red"
        Write-Color "Please install Docker to run Qdrant" "Yellow"
        exit 1
    }
    
    # Check if qdrant-thoth container exists
    $existingContainer = & docker ps -a --format "table {{.Names}}" | Where-Object { $_ -eq "qdrant-thoth" }
    
    if ($existingContainer) {
        Write-Color "Starting existing qdrant-thoth container..." "Yellow"
        & docker start qdrant-thoth
        $Global:QdrantContainer = "qdrant-thoth"
    }
    else {
        Write-Color "Creating and starting new qdrant-thoth container..." "Yellow"
        $currentPath = (Get-Location).Path
        & docker run -d --name qdrant-thoth -p "6334:6333" -v "${currentPath}/qdrant_storage:/qdrant/storage:z" qdrant/qdrant
        $Global:QdrantContainer = "qdrant-thoth"
    }
    
    # Wait for Qdrant to start
    Write-Color "Waiting for Qdrant to start..." "Yellow"
    $attempts = 30
    for ($i = 1; $i -le $attempts; $i++) {
        if (Test-Port $QdrantPort) {
            Write-Color "✓ Qdrant started successfully on port $QdrantPort" "Green"
            break
        }
        Start-Sleep -Seconds 1
    }
    
    if (-not (Test-Port $QdrantPort)) {
        Write-Color "Failed to start Qdrant" "Red"
        exit 1
    }
}

# Check and start SQL Generator (with cleanup)
Write-Color "Checking SQL Generator on port $SqlGeneratorPort..." "Yellow"

# Always cleanup existing SQL Generator processes first
Stop-SqlGeneratorProcesses

if (Test-Port $SqlGeneratorPort) {
    Write-Color "Port $SqlGeneratorPort still in use, killing processes..." "Yellow"
    Stop-ProcessOnPort $SqlGeneratorPort
}

Write-Color "Starting SQL Generator..." "Yellow"
# Ensure uv is available for the SQL Generator (it uses pyproject.toml/uv.lock)
if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Color "Error: 'uv' is required to run the SQL Generator locally." "Red"
    Write-Color "Install with: Invoke-WebRequest -Uri https://astral.sh/uv/install.ps1 | Invoke-Expression" "Yellow"
    exit 1
}

Push-Location $SqlGenDir

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-Color "Creating virtual environment for SQL Generator..." "Yellow"
    $env:VIRTUAL_ENV = $null
    & uv sync
}
else {
    Write-Color "Updating SQL Generator dependencies..." "Yellow"
    $env:VIRTUAL_ENV = $null
    & uv sync
}

# Start SQL Generator
$env:VIRTUAL_ENV = $null
$env:PORT = $SqlGeneratorPort
$process = Start-Process -FilePath "uv" -ArgumentList "run", "python", "main.py" -PassThru -WindowStyle Hidden
$Global:ProcessIds["SqlGenerator"] = $process.Id

Pop-Location

# Wait for SQL Generator to start
Write-Color "Waiting for SQL Generator to start..." "Yellow"
$attempts = 30
for ($i = 1; $i -le $attempts; $i++) {
    if (Test-Port $SqlGeneratorPort) {
        Write-Color "✓ SQL Generator started successfully on port $SqlGeneratorPort" "Green"
        break
    }
    Start-Sleep -Seconds 1
}

if (-not (Test-Port $SqlGeneratorPort)) {
    Write-Color "Failed to start SQL Generator" "Red"
    exit 1
}

# Check and start Frontend (Next.js)
Write-Color "Checking Frontend on port $FrontendPort..." "Yellow"
if (Test-Port $FrontendPort) {
    Write-Color "✓ Frontend is already running on port $FrontendPort" "Green"
}
else {
    Write-Color "Frontend is NOT running on port $FrontendPort" "Yellow"
    Write-Color "Starting Frontend..." "Yellow"
    
    # Check if frontend directory exists
    if (Test-Path "frontend") {
        Push-Location "frontend"
        
        # Check if node_modules exists
        if (-not (Test-Path "node_modules")) {
            # Ensure Node.js/npm is installed
            if (-not (Get-Command "npm" -ErrorAction SilentlyContinue)) {
                Write-Color "Error: npm is not installed. Please install Node.js (v20+) and retry." "Red"
                exit 1
            }
            Write-Color "Installing Frontend dependencies..." "Yellow"
            & npm install
        }
        
        # Start Frontend with specific port
        $env:PORT = $FrontendPort
        $process = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -PassThru -WindowStyle Hidden
        $Global:ProcessIds["Frontend"] = $process.Id
        
        Pop-Location
        
        # Wait for Frontend to start
        Write-Color "Waiting for Frontend to start..." "Yellow"
        $attempts = 30
        for ($i = 1; $i -le $attempts; $i++) {
            if (Test-Port $FrontendPort) {
                Write-Color "✓ Frontend started successfully on port $FrontendPort" "Green"
                break
            }
            Start-Sleep -Seconds 1
        }
        
        if (-not (Test-Port $FrontendPort)) {
            Write-Color "Failed to start Frontend" "Red"
            exit 1
        }
    }
    else {
        Write-Color "Frontend directory not found!" "Red"
        exit 1
    }
}

# Display service information
Write-Host ""
Write-Color "All services started successfully!" "Green"
Write-Host "==========================================="
Write-Color "Service URLs:" "Blue"
Write-Color "   Frontend App:     http://localhost:$FrontendPort" "Green"
Write-Color "   Backend Home:     http://localhost:$BackendPort" "Green"
Write-Color "   Django Admin:     http://localhost:$BackendPort/admin" "Green"
Write-Color "   SQL Generator:    http://localhost:$SqlGeneratorPort" "Green"
Write-Color "   API Docs:         http://localhost:$SqlGeneratorPort/docs" "Green"
Write-Color "   Qdrant API:       http://localhost:$QdrantPort" "Green"

# Function to handle cleanup
function Invoke-Cleanup {
    Write-Host ""
    Write-Color "Stopping services..." "Yellow"
    
    # Stop Frontend
    if ($Global:ProcessIds["Frontend"]) {
        try {
            Stop-Process -Id $Global:ProcessIds["Frontend"] -Force -ErrorAction SilentlyContinue
            Write-Color "✓ Frontend stopped" "Green"
        }
        catch {
            # Ignore errors
        }
    }
    
    # Stop SQL Generator
    if ($Global:ProcessIds["SqlGenerator"]) {
        try {
            Stop-Process -Id $Global:ProcessIds["SqlGenerator"] -Force -ErrorAction SilentlyContinue
            Write-Color "✓ SQL Generator stopped" "Green"
        }
        catch {
            # Ignore errors
        }
    }
    
    # Stop Django if we started it
    if ($Global:ProcessIds["Django"]) {
        Write-Color "Stopping Django backend..." "Yellow"
        try {
            Stop-Process -Id $Global:ProcessIds["Django"] -Force -ErrorAction SilentlyContinue
            Write-Color "✓ Django backend stopped" "Green"
        }
        catch {
            # Ignore errors
        }
    }
    
    # Ask about Qdrant container
    if ($Global:QdrantContainer) {
        $response = Read-Host "Stop Qdrant container? (y/N)"
        if ($response -match "^[Yy]") {
            & docker stop $Global:QdrantContainer
            Write-Color "✓ Qdrant container stopped" "Green"
        }
        else {
            Write-Color "Qdrant container left running" "Yellow"
        }
    }
    
    Write-Color "All services stopped" "Green"
    exit 0
}

# Set up Ctrl+C handler
Register-EngineEvent PowerShell.Exiting -Action { Invoke-Cleanup }

Write-Host ""
Write-Color "===========================================" "Blue"
Write-Color "All services are running. Press Ctrl+C to stop all services." "Green"
Write-Color "===========================================" "Blue"

# Wait for user input to keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Invoke-Cleanup
}