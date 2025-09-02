# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# PowerShell script to prepare Docker environment after initial install

Write-Host "Preparing Docker environment..." -ForegroundColor Green

# Check if config.yml.local exists
if (-not (Test-Path "config.yml.local")) {
    Write-Host "ERROR: config.yml.local not found!" -ForegroundColor Red
    Write-Host "Please run ./install.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Create .env.docker if it doesn't exist
if (-not (Test-Path ".env.docker")) {
    Write-Host "Creating .env.docker from template..." -ForegroundColor Yellow
    
    if (Test-Path ".env.docker.example") {
        Copy-Item ".env.docker.example" ".env.docker"
        Write-Host "Created .env.docker from .env.docker.example" -ForegroundColor Green
    }
    elseif (Test-Path ".env.template") {
        Copy-Item ".env.template" ".env.docker"
        Write-Host "Created .env.docker from .env.template" -ForegroundColor Green
    }
    else {
        # Create a minimal .env.docker
        @"
# Docker environment variables
NODE_ENV=production
DJANGO_DEBUG=False
PYTHONUNBUFFERED=1
"@ | Out-File -FilePath ".env.docker" -Encoding UTF8
        Write-Host "Created minimal .env.docker" -ForegroundColor Green
    }
}

# Fix line endings for shell scripts (if in WSL)
if ($IsLinux -or (Test-Path "/usr/bin/dos2unix")) {
    Write-Host "Fixing line endings for shell scripts..." -ForegroundColor Yellow
    & bash -c "./scripts/prepare-docker-build.sh"
}

# Create necessary directories
$directories = @("data_exchange", "logs", "backend/logs", "frontend/logs")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "Created directory: $dir" -ForegroundColor Gray
    }
}

Write-Host "`nEnvironment prepared!" -ForegroundColor Green
Write-Host "`nYou can now run:" -ForegroundColor Yellow
Write-Host "  docker-compose build" -ForegroundColor White
Write-Host "  docker-compose up" -ForegroundColor White
Write-Host "`nOr use the shortcut:" -ForegroundColor Yellow
Write-Host "  docker-compose up --build" -ForegroundColor White