@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the Apache License 2.0.
REM See the LICENSE.md file in the project root for full license information.

echo ============================================================
echo Starting ThothAI with Docker
echo ============================================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Check if setup has been run
docker volume ls | findstr thoth-shared-data >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Running setup first...
    call setup-docker.bat
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Setup failed!
        pause
        exit /b 1
    )
)

REM Start Docker Compose
echo Starting Docker Compose...
echo.
docker-compose up --build

pause