#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Start all Thoth UI services with SQL Generator in debug mode

echo "Starting Thoth UI Services in DEBUG MODE..."
echo "============================================="

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

# Clean up any existing processes first
cleanup_sql_generator

# Check required ports and offer to clean them
echo "Checking ports..."

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

check_port 8040 || echo "Port 8040 (Django Backend) is in use - assuming backend is running"

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
echo "Starting SQL Generator service in DEBUG MODE..."
echo "   - Debug port: 5678 (for debugpy)"
echo "   - You can attach your debugger to localhost:5678"
echo ""

# Start SQL Generator with debugpy for remote debugging
uv run python -m debugpy --listen 0.0.0.0:5678 --wait-for-client main.py &
SQL_GEN_PID=$!

echo "Waiting for debugger to attach on port 5678..."
echo "   Connect your debugger (VS Code, PyCharm, etc.) to localhost:5678"
echo ""

cd ..

echo ""
echo "Starting Next.js frontend..."
npm run dev &
NEXT_PID=$!

echo ""
echo "All services started in DEBUG MODE!"
echo ""
echo "Service URLs:"
echo "   - Frontend:      http://localhost:3000"
echo "   - SQL Generator: http://localhost:8001"
echo "   - API Docs:      http://localhost:8001/docs"
echo "   - Debug Port:    localhost:5678 (debugpy)"
echo ""
echo "Debug Instructions:"
echo "   1. The SQL Generator is waiting for a debugger to attach"
echo "   2. Configure your IDE to connect to localhost:5678"
echo "   3. Once connected, the SQL Generator will start"
echo ""
echo "   VS Code launch.json example:"
echo '   {
       "name": "Attach to SQL Generator",
       "type": "python",
       "request": "attach",
       "connect": {
           "host": "localhost",
           "port": 5678
       },
       "pathMappings": [
           {
               "localRoot": "${workspaceFolder}/sql_generator",
               "remoteRoot": "."
           }
       ]
   }'
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