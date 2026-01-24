# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

# Clean ThothAI environment to first startup conditions
# Resets database and Qdrant storage

$ErrorActionPreference = "Continue"

# Paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Cleaning ThothAI Environment" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

# --- Load .env.local ---
if (Test-Path ".env.local") {
    Write-Host "Loading configuration from .env.local..."
    Get-Content ".env.local" | ForEach-Object {
        if ($_ -match "^(?<name>[^#\s=]+)=(?<value>.*)$") {
            $name = $Matches.name.Trim()
            $value = $Matches.value.Trim()
            # Remove quotes if present
            if ($value -match "^'.*'$" -or $value -match '^".*"$') {
                $value = $value.Substring(1, $value.Length - 2)
            }
            [Environment]::SetEnvironmentVariable($name, $value)
        }
    }
} else {
    Write-Host "[!] .env.local not found. Nothing to clean based on config." -ForegroundColor Red
    exit 1
}

# Standardize variables
$DB_SCHEMA = if ($env:DB_SCHEMA) { $env:DB_SCHEMA } else { "thoth_db" }
$QDRANT_LOCAL_STORAGE = "./qdrant_storage_local"

# --- Step 1: Stop Services ---
Write-Host "Step 1: Stopping all services..." -ForegroundColor Blue
& (Join-Path $ScriptDir "stop-all.ps1")
Write-Host "  Services stopped."

# --- Step 2: Clean Postgres ---
Write-Host "Step 2: Cleaning Postgres database..." -ForegroundColor Blue
if ($env:DATABASE_URL) {
    if ((Get-Command "psql" -ErrorAction SilentlyContinue)) {
        Write-Host "  Using DATABASE_URL and schema $DB_SCHEMA"
        $sql = "DROP SCHEMA IF EXISTS thoth_schema CASCADE; DROP SCHEMA IF EXISTS $DB_SCHEMA CASCADE; CREATE SCHEMA $DB_SCHEMA;"
        psql $env:DATABASE_URL -c "$sql"
        Write-Host "  Postgres schema $DB_SCHEMA reset." -ForegroundColor Green
    } else {
        Write-Host "  [!] psql command not found. Cannot reset Postgres." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [*] DATABASE_URL not set. Skipping Postgres cleanup." -ForegroundColor Gray
}

# --- Step 3: Clean Qdrant Local Storage ---
Write-Host "Step 3: Cleaning Qdrant local storage..." -ForegroundColor Blue
if (Test-Path $QDRANT_LOCAL_STORAGE) {
    Remove-Item -Path $QDRANT_LOCAL_STORAGE -Recurse -Force
    Write-Host "  Deleted $QDRANT_LOCAL_STORAGE." -ForegroundColor Green
} else {
    Write-Host "  $QDRANT_LOCAL_STORAGE not found." -ForegroundColor Gray
}

# --- Step 4: Clean SQLite (Optional fallback) ---
$sqlitePath = "backend/db.sqlite3"
if (Test-Path $sqlitePath) {
    Write-Host "Step 4: Cleaning local SQLite..." -ForegroundColor Blue
    Remove-Item -Path $sqlitePath -Force
    Write-Host "  Deleted $sqlitePath." -ForegroundColor Green
}

Write-Host ""
Write-Host "============================" -ForegroundColor Cyan
Write-Host "Environment reset completed!" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
