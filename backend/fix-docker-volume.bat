@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the Apache License 2.0.
REM See the LICENSE.md file in the project root for full license information.

REM Script to fix/repair Docker volume if dev_databases is missing

setlocal EnableDelayedExpansion

echo ============================================================
echo     ThothAI Docker Volume Repair Tool
echo ============================================================
echo.
echo This script will check and repair the Docker volume
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

REM Check if volume exists
docker volume ls | findstr "thoth-shared-data" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker volume 'thoth-shared-data' does not exist.
    echo Run install.bat or setup-docker.bat first.
    pause
    exit /b 1
)

echo Checking current volume contents...
docker run --rm -v thoth-shared-data:/target alpine sh -c "ls -la /target/"

REM Get current directory with proper escaping for Docker
set "CURRENT_DIR=%CD%"
set "CURRENT_DIR=!CURRENT_DIR:\=/!"

REM Check if dev_databases exists in the local data directory
if not exist "data\dev_databases" (
    echo.
    echo ERROR: No dev_databases found in local data directory
    echo Make sure you have the data\dev_databases folder in your project
    pause
    exit /b 1
)

echo.
echo Forcing copy of dev_databases to Docker volume...

REM Force copy dev_databases
docker run --rm -v "!CURRENT_DIR!/data:/source:ro" -v thoth-shared-data:/target alpine sh -c "rm -rf /target/dev_databases 2>/dev/null; cp -r /source/dev_databases /target/ && echo 'COPY_SUCCESS' || echo 'COPY_FAILED'"

REM Check if copy was successful
docker run --rm -v thoth-shared-data:/target alpine sh -c "test -d /target/dev_databases && echo 'SUCCESS: dev_databases copied' || echo 'ERROR: Copy failed'"

REM Also ensure db.sqlite3 is copied
if exist "data\db.sqlite3" (
    docker run --rm -v "!CURRENT_DIR!/data:/source:ro" -v thoth-shared-data:/target alpine sh -c "cp -f /source/db.sqlite3 /target/ 2>/dev/null"
    echo db.sqlite3 copied
)

echo.
echo Final volume contents:
docker run --rm -v thoth-shared-data:/target alpine sh -c "ls -la /target/"

echo.
echo ============================================================
echo Volume repair complete!
echo You can now run: docker-compose up --build
echo ============================================================
echo.
pause

endlocal