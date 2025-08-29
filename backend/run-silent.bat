@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the Apache License 2.0.
REM See the LICENSE.md file in the project root for full license information.

REM Silent runner for Thoth Docker containers (Windows)
REM Provides minimal output with progress indicators

setlocal enabledelayedexpansion

REM Default values
set REBUILD=0
set CLEAN_BUILD=0
set SERVICES=app db qdrant proxy

REM Parse arguments silently
:parse_args
if "%~1"=="" goto end_parse
if /i "%~1"=="-b" set REBUILD=1
if /i "%~1"=="--build" set REBUILD=1
if /i "%~1"=="-c" (
    set CLEAN_BUILD=1
    set REBUILD=1
)
if /i "%~1"=="--clean" (
    set CLEAN_BUILD=1
    set REBUILD=1
)
if /i "%~1"=="-s" (
    set SERVICES=%~2
    shift
)
if /i "%~1"=="--services" (
    set SERVICES=%~2
    shift
)
if /i "%~1"=="-h" goto show_help
if /i "%~1"=="--help" goto show_help
shift
goto parse_args
:end_parse

echo Thoth Docker Runner (Silent Mode)
echo =================================

REM Check _env file
echo|set /p="[1/5] Checking environment..."
if not exist "_env" (
    echo  Warning (_env missing)
) else (
    echo  OK
)

REM Build if needed
if !REBUILD!==1 (
    if !CLEAN_BUILD!==1 (
        echo|set /p="[2/5] Clean building..."
        docker compose build --no-cache app proxy >nul 2>&1
        if errorlevel 1 (
            echo  FAILED
            exit /b 1
        )
        echo  OK
    ) else (
        echo|set /p="[2/5] Building..."
        docker compose build app proxy >nul 2>&1
        if errorlevel 1 (
            echo  FAILED
            exit /b 1
        )
        echo  OK
    )
) else (
    REM Check if images exist
    docker images | findstr "thoth_be-app" >nul
    set APP_EXISTS=!errorlevel!
    docker images | findstr "thoth-be-proxy" >nul
    set PROXY_EXISTS=!errorlevel!
    
    if !APP_EXISTS!==1 (
        set NEED_BUILD=1
    )
    if !PROXY_EXISTS!==1 (
        set NEED_BUILD=1
    )
    
    if defined NEED_BUILD (
        echo|set /p="[2/5] Building (first time)..."
        docker compose build app proxy >nul 2>&1
        if errorlevel 1 (
            echo  FAILED
            exit /b 1
        )
        echo  OK
    ) else (
        echo [2/5] Images ready... OK
    )
)

REM Stop existing containers
echo|set /p="[3/5] Stopping existing..."
docker compose stop !SERVICES! >nul 2>&1
echo  OK

REM Start containers
echo|set /p="[4/5] Starting services..."
docker compose up -d !SERVICES! >nul 2>&1
if errorlevel 1 (
    echo  FAILED
    exit /b 1
)
echo  OK

REM Check status
echo|set /p="[5/5] Verifying..."
timeout /t 2 /nobreak >nul
for /f %%i in ('docker compose ps --services --filter "status=running" 2^>nul ^| find /c /v ""') do set RUNNING=%%i
for %%i in (!SERVICES!) do set /a EXPECTED+=1
if !RUNNING! geq !EXPECTED! (
    echo  OK
) else (
    echo  WARNING (partial)
)

echo.
echo Status: All services started
echo Access: http://localhost:8040
echo.

exit /b 0

:show_help
echo Usage: %~nx0 [-b^|--build] [-c^|--clean] [-s^|--services SERVICES]
exit /b 0