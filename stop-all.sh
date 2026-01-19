#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Stop all locally running ThothAI services

echo "Stopping ThothAI local services..."

# Kill Python processes
pkill -f "manage.py runserver" 2>/dev/null && echo "  Stopped backend"
pkill -f "sql_generator/main.py" 2>/dev/null && echo "  Stopped sql-generator"
pkill -f "sql_generator.*main.py" 2>/dev/null

# Kill Next.js
pkill -f "next dev" 2>/dev/null && echo "  Stopped frontend"
pkill -f "npm run dev" 2>/dev/null

# Stop local Qdrant container
docker stop thoth-qdrant-local 2>/dev/null && echo "  Stopped qdrant-local"
docker rm thoth-qdrant-local 2>/dev/null

echo "All local services stopped."
