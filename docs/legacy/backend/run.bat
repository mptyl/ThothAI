@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the Apache License 2.0.
REM See the LICENSE.md file in the project root for full license information.

setlocal enabledelayedexpansion

REM Default values
set REBUILD=0
set CLEAN_BUILD=0
set FOLLOW_LOGS=0
set SERVICES=app db qdrant proxy

REM Parse arguments
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
if /i "%~1"=="-f" set FOLLOW_LOGS=1
if /i "%~1"=="--follow" set FOLLOW_LOGS=1
if /i "%~1"=="-h" goto show_help
if /i "%~1"=="--help" goto show_help
if /i "%~1"=="-s" (
    set SERVICES=%~2
    shift
)
if /i "%~1"=="--services" (
    set SERVICES=%~2
    shift
)
shift
goto parse_args
:end_parse

echo.
echo Thoth Docker Runner
echo ========================
echo.

REM Check if _env file exists
if not exist "_env" (
    echo WARNING: _env file not found!
    echo Copy _env.template to _env and configure it.
    echo.
)

REM Build if requested or if image doesn't exist
if !REBUILD!==1 (
    if !CLEAN_BUILD!==1 (
        echo Starting clean build (no cache)...
        echo   - Building Django backend application (app)
        echo   - Building Nginx proxy server (proxy)
        echo   - This will take 3-5 minutes for first build
        echo.
        docker compose build --no-cache app proxy
    ) else (
        echo Building containers...
        echo   - Building Django backend application (app)
        echo   - Building Nginx proxy server (proxy)
        echo   - Using cache for faster builds
        echo.
        docker compose build app proxy
    )
    
    if errorlevel 1 (
        echo ERROR: Build failed!
        exit /b 1
    )
    echo.
    echo Build completed!
    echo.
) else (
    REM Check if images exist
    echo Checking for existing Docker images...
    docker images | findstr "thoth_be-app" >nul
    set APP_EXISTS=!errorlevel!
    docker images | findstr "thoth-be-proxy" >nul
    set PROXY_EXISTS=!errorlevel!
    
    if !APP_EXISTS!==1 (
        echo Django app image not found - will build
        set NEED_BUILD=1
    )
    if !PROXY_EXISTS!==1 (
        echo Nginx proxy image not found - will build
        set NEED_BUILD=1
    )
    
    if defined NEED_BUILD (
        echo Building required images...
        echo First-time build typically takes 3-5 minutes
        echo.
        docker compose build app proxy
        
        if errorlevel 1 (
            echo ERROR: Build failed!
            exit /b 1
        )
        echo.
        echo Build completed!
        echo.
    ) else (
        echo All required images found!
        echo   - Django app image: ready
        echo   - Nginx proxy image: ready
        echo.
    )
)

REM Stop any running containers first
echo Stopping any existing containers...
docker compose stop !SERVICES! >nul 2>&1

REM Start containers in detached mode
echo Starting containers in detached mode...
echo   - PostgreSQL database (db)
echo   - Qdrant vector database (qdrant)
echo   - Django backend application (app)
echo   - Nginx proxy server (proxy)
docker compose up -d !SERVICES!

if errorlevel 1 (
    echo ERROR: Failed to start containers!
    echo Check the logs with: docker compose logs
    exit /b 1
)

echo.
echo All containers started successfully!
echo.

REM Show container status
echo Container Status:
docker compose ps

echo.
echo Access URLs:
echo   Django Admin: http://localhost:8040/admin
echo   API: http://localhost:8040/api/
echo   Qdrant UI: http://localhost:6333/dashboard

REM Follow logs if requested
if !FOLLOW_LOGS!==1 (
    echo.
    echo Following logs (Ctrl+C to stop)...
    echo.
    docker compose logs -f !SERVICES!
) else (
    echo.
    echo Tips:
    echo   View logs:        docker compose logs -f
    echo   Stop containers:  docker compose stop
    echo   Remove all:       docker compose down
    echo   Shell access:     docker compose exec app bash
)

exit /b 0

:show_help
echo Usage: %~nx0 [OPTIONS]
echo.
echo Build and run Thoth Docker containers
echo.
echo Options:
echo   -b, --build         Force rebuild before starting
echo   -c, --clean         Clean build (no cache)
echo   -f, --follow        Follow logs after starting
echo   -s, --services      Specify services (default: app db qdrant proxy)
echo   -h, --help          Show this help message
echo.
echo Examples:
echo   %~nx0                    # Start all services (build if needed)
echo   %~nx0 -b                 # Rebuild and start
echo   %~nx0 -c                 # Clean rebuild and start
echo   %~nx0 -f                 # Start and follow logs
echo   %~nx0 -b -f              # Rebuild, start, and follow logs
echo   %~nx0 -s app             # Start only app service
exit /b 0