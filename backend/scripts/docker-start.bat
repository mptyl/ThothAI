@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the MIT License.
REM See the LICENSE.md file in the project root for full license information.

REM Run Thoth with local Docker Compose (no cache issues)

echo Starting Thoth services...
docker compose -f docker-compose.local.yml up --build -d

echo.
echo Thoth services started successfully!
echo.
echo Access points:
echo   - Admin: http://localhost:8040/admin
echo   - API: http://localhost:8040/api
echo   - Qdrant: http://localhost:6333
echo.
echo Use 'docker compose -f docker-compose.local.yml logs -f' to view logs
echo Use 'docker compose -f docker-compose.local.yml down' to stop services