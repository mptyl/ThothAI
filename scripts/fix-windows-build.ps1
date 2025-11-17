# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# PowerShell script to fix Windows Docker build issues

Write-Host "Fixing potential Windows Docker build issues..." -ForegroundColor Green

# Check if frontend/lib/contexts directory exists
if (-not (Test-Path "frontend\lib\contexts")) {
    Write-Host "ERROR: frontend\lib\contexts directory not found!" -ForegroundColor Red
    exit 1
}

# Check if workspace-context.tsx exists
if (-not (Test-Path "frontend\lib\contexts\workspace-context.tsx")) {
    Write-Host "ERROR: workspace-context.tsx not found!" -ForegroundColor Red
    exit 1
}

Write-Host "File structure looks correct." -ForegroundColor Green
Write-Host ""
Write-Host "Files in frontend\lib\contexts:" -ForegroundColor Yellow
Get-ChildItem -Path "frontend\lib\contexts" | Format-Table Name, Length, LastWriteTime

Write-Host ""
Write-Host "Cleaning Docker cache..." -ForegroundColor Yellow
docker-compose down
docker system prune -f

Write-Host ""
Write-Host "Now rebuilding frontend service..." -ForegroundColor Green
docker-compose build --no-cache frontend

Write-Host ""
Write-Host "Build complete. Try running:" -ForegroundColor Green
Write-Host "  docker-compose up" -ForegroundColor Cyan