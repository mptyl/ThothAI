#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Start all ThothAI UI services

echo "Starting ThothAI UI Services..."
echo "================================"

# Check if .env.local exists
if [ ! -f .env.local ]; then
    echo "Creating .env.local from template..."
    cp .env.local.template .env.local
    echo "Please edit .env.local to add an AI provider API key:"
    echo "   - OPENAI_API_KEY (for OpenAI GPT models)"
    echo "   - ANTHROPIC_API_KEY (for Claude models)"
    echo "   - MISTRAL_API_KEY (for Mistral models)"
    echo "   - OLLAMA_API_BASE (for local Ollama models)"
    echo ""
fi

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "Port $1 is already in use"
        return 1
    fi
    return 0
}

# Function to kill processes on a specific port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo "Killing processes on port $port: $pids"
        kill $pids 2>/dev/null
        sleep 2
        # Force kill if still running
        local remaining=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$remaining" ]; then
            echo "Force killing remaining processes: $remaining"
            kill -9 $remaining 2>/dev/null
        fi
    fi
}

# Function to cleanup SQL Generator processes
cleanup_sql_generator() {
    echo "Cleaning up any existing SQL Generator processes..."
    pkill -f "python.*main\.py" 2>/dev/null || true
    pkill -f "sql_generator" 2>/dev/null || true
    sleep 1
}

# Check required services first
echo "Checking required services..."

# Check if Django backend is running on port 8200
if lsof -Pi :8200 -sTCP:LISTEN -t >/dev/null ; then
    echo "Django backend is running on port 8200"
else
    echo "Django backend is NOT running on port 8200"
    echo "   Please start the Django backend first:"
    echo "   cd ../thoth_be && python manage.py runserver 8200"
    exit 1
fi

# Check if Qdrant is running on port 6334
if lsof -Pi :6334 -sTCP:LISTEN -t >/dev/null ; then
    echo "Qdrant is running on port 6334"
else
    echo "Qdrant is NOT running on port 6334"
    echo "   Please start Qdrant first:"
    echo "   docker run -p 6334:6334 qdrant/qdrant"
    exit 1
fi

echo ""

# Clean up any existing processes first
cleanup_sql_generator

# Check required ports and offer to clean them
echo "Checking application ports..."

if ! check_port 3000; then
    read -p "Kill processes on port 3000? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill_port 3000
    else
        echo "Cannot start - port 3000 is in use"; exit 1
    fi
fi

if ! check_port 8001; then
    echo "Port 8001 is already in use"
    echo "   This might be the Docker container running the SQL Generator service."
    echo "   If Docker is running, the SQL Generator is accessible at port 8005."
    echo ""
    echo "   Options:"
    echo "   1. Stop the Docker container if you want to run locally"
    echo "   2. Use the Docker service (accessible at port 8005)"
    echo ""
    read -p "Do you want to continue with the local setup anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting. Please stop the Docker container or use port 8005 for the SQL Generator."; exit 1
    fi
fi

echo ""
echo "Installing dependencies..."
npm install

echo ""
echo "Setting up SQL Generator..."
cd sql_generator

# Check if uv virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating UV virtual environment and installing dependencies..."
    uv sync --isolated
else
    echo "UV virtual environment exists, updating dependencies..."
    # Ensure all dependencies are up to date, including tzlocal
    uv sync --isolated
fi

echo ""
echo "Starting SQL Generator service..."
# Load environment variables from .env files
# The SQL Generator will load these from .env.local automatically
# No need to export them here as it would override the .env.local values

uv run python main.py &
SQL_GEN_PID=$!

cd ..

echo ""
echo "Starting Next.js frontend..."
npm run dev &
NEXT_PID=$!

echo ""
echo "All services started!"
echo ""
echo "Service URLs:"
echo "   - Frontend:      http://localhost:3000"
echo "   - SQL Generator: http://localhost:8001"
echo "   - API Docs:      http://localhost:8001/docs"

# Check for Logfire token and show URL if available
if [ -f .env.local ]; then
    LOGFIRE_TOKEN=$(grep "^LOGFIRE_TOKEN=" .env.local | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    if [ ! -z "$LOGFIRE_TOKEN" ] && [ "$LOGFIRE_TOKEN" != "" ]; then
        echo ""
        echo "Logfire Dashboard:"
        echo "   - View logs at: https://logfire.pydantic.dev/"
        echo "   - Project: Your project should appear after the first log"
        echo "   - Token configured: Yes"
    else
        echo ""
        echo "Logfire:"
        echo "   - Status: Not configured (no LOGFIRE_TOKEN in .env.local)"
        echo "   - To enable: Add LOGFIRE_TOKEN to .env.local"
        echo "   - Get token at: https://logfire.pydantic.dev/"
    fi
fi

echo ""
echo "To stop all services, press Ctrl+C"
echo ""

# Function to handle cleanup
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $SQL_GEN_PID 2>/dev/null
    kill $NEXT_PID 2>/dev/null
    echo "All services stopped"
    exit 0
}

# Set up trap to catch Ctrl+C
trap cleanup INT

# Wait for services
wait