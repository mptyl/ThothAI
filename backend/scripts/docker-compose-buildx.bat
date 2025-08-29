@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the MIT License.
REM See the LICENSE.md file in the project root for full license information.

REM Build and run Docker Compose with Buildx support on Windows

echo Building Thoth with Docker Buildx...

REM Check if buildx builder exists
docker buildx inspect thoth-builder >nul 2>&1
if errorlevel 1 (
    echo Creating buildx builder...
    call scripts\setup-buildx.bat
)

REM Build each service with buildx
echo.
echo Building thoth-be service...
docker buildx build ^
    --cache-from type=local,src=.buildcache ^
    --cache-to type=local,dest=.buildcache,mode=max ^
    --tag thoth-be:latest ^
    --load ^
    -f Dockerfile ^
    .

echo.
echo Building thoth-be-proxy service...
docker buildx build ^
    --cache-from type=local,src=.buildcache-proxy ^
    --cache-to type=local,dest=.buildcache-proxy,mode=max ^
    --tag thoth-be-proxy:v2 ^
    --load ^
    -f proxy/Dockerfile ^
    proxy

echo.
echo Starting services with docker compose...
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d

echo.
echo Services started successfully!