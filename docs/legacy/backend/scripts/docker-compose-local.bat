@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the MIT License.
REM See the LICENSE.md file in the project root for full license information.

REM Run Docker Compose with local override (no registry cache)

echo Starting Thoth with local Docker Compose configuration...
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build -d

echo.
echo Services started successfully!
echo Use 'docker compose logs -f' to view logs