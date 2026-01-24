# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

# Stop all locally running ThothAI services

$ErrorActionPreference = "Continue"

Write-Host "Stopping ThothAI local services..." -ForegroundColor Cyan

# 1. Stop Python processes (Backend and SQL Generator)
Write-Host "  Stopping Python services..." -ForegroundColor Yellow
$pythonProcs = Get-Process | Where-Object { $_.Path -like "*python*" -and ($_.CommandLine -like "*manage.py runserver*" -or $_.CommandLine -like "*sql_generator/main.py*" -or $_.CommandLine -like "*sql_generator.*main.py*") }
if ($pythonProcs) {
    $pythonProcs | Stop-Process -Force
    Write-Host "  Stopped Python services." -ForegroundColor Green
}

# 2. Stop Node.js processes (Frontend)
Write-Host "  Stopping Node.js services..." -ForegroundColor Yellow
$nodeProcs = Get-Process | Where-Object { $_.Name -eq "node" -and ($_.CommandLine -like "*next dev*" -or $_.CommandLine -like "*npm run dev*") }
if ($nodeProcs) {
    $nodeProcs | Stop-Process -Force
    Write-Host "  Stopped Node.js frontend." -ForegroundColor Green
}

# 3. Stop local Qdrant container
if ((Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "  Stopping Qdrant container..." -ForegroundColor Yellow
    docker stop thoth-qdrant-local 2>$null | Out-Null
    docker rm thoth-qdrant-local 2>$null | Out-Null
    Write-Host "  Stopped qdrant-local." -ForegroundColor Green
}

Write-Host "All local services stopped." -ForegroundColor Cyan
