#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Start all ThothAI services
# This script starts Frontend, Django backend, Qdrant, and SQL Generator services

echo "Starting ThothAI Services..."
echo "============================="

# Configuration
SQL_GEN_DIR="frontend/sql_generator"

# Load environment variables from root .env.local
if [ -f .env.local ]; then
    echo "Loading environment from .env.local"
    set -a
    . ./.env.local
    set +a
    # Avoid leaking a generic PORT that could clash with service-specific ports
    unset PORT || true
else
    echo "Error: .env.local not found in root directory"
    
    # Try to create from template
    if [ -f .env.local.template ]; then
        echo -e "${YELLOW}Creating .env.local from .env.local.template...${NC}"
        cp .env.local.template .env.local
        echo -e "${GREEN}✓ .env.local created successfully${NC}"
        echo ""
        echo -e "${YELLOW}IMPORTANT: Please edit .env.local and add your API keys:${NC}"
        echo -e "  - At least one AI provider (OpenAI, Anthropic, Gemini, etc.)"
        echo -e "  - DJANGO_API_KEY (change from default)"
        echo -e "  - Other configuration as needed"
        echo ""
        echo -e "${YELLOW}After editing .env.local, run ./start-all.sh again${NC}"
        exit 0
    else
        echo "Template file .env.local.template not found"
        echo "Please create .env.local manually or restore .env.local.template"
        exit 1
    fi
fi

# Port configuration from environment
FRONTEND_PORT=${FRONTEND_PORT:-3200}
SQL_GENERATOR_PORT=${SQL_GENERATOR_PORT:-8180}
BACKEND_PORT=${BACKEND_PORT:-8200}
QDRANT_PORT=6334

# Global PIDs for cleanup
DJANGO_PID=""
QDRANT_CONTAINER=""
SQL_GEN_PID=""
FRONTEND_PID=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    fi
    return 1  # Port is free
}

# Function to kill processes on a specific port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}Killing processes on port $port: $pids${NC}"
        kill $pids 2>/dev/null
        sleep 2
        # Force kill if still running
        local remaining=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$remaining" ]; then
            echo -e "${YELLOW}Force killing remaining processes: $remaining${NC}"
            kill -9 $remaining 2>/dev/null
        fi
    fi
}

# Function to cleanup SQL Generator processes
cleanup_sql_generator() {
    echo -e "${YELLOW}Cleaning up any existing SQL Generator processes...${NC}"
    pkill -f "python.*main\.py" 2>/dev/null || true
    pkill -f "sql_generator" 2>/dev/null || true
    sleep 1
}

# Main script starts here
echo -e "${BLUE}ThothAI Service Startup Script${NC}"
echo "==============================="

# Step 1: Check and start all required services
echo -e "\n${YELLOW}Step 1: Starting all services...${NC}"

# Check and start Django backend
if check_port $BACKEND_PORT; then
    echo -e "${GREEN}✓ Django backend is already running on port $BACKEND_PORT${NC}"
else
    echo -e "${YELLOW}Django backend is NOT running on port $BACKEND_PORT${NC}"
    echo -e "${YELLOW}Starting Django backend...${NC}"
    
    # Check if backend directory exists
    if [ -d "backend" ]; then
        cd backend
        
        # Check if virtual environment exists
        if [ -d ".venv" ]; then
            # Use uv to run Django if available
            if command -v uv &> /dev/null; then
                echo -e "${GREEN}Starting Django with uv...${NC}"
                # Django will use environment variables already exported from root .env.local
                # Unset VIRTUAL_ENV to avoid conflicts with uv's environment detection
                (unset VIRTUAL_ENV && uv run python manage.py runserver $BACKEND_PORT) &
                DJANGO_PID=$!
            else
                # Fallback to regular Python
                echo -e "${GREEN}Starting Django with Python...${NC}"
                source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
                python manage.py runserver $BACKEND_PORT &
                DJANGO_PID=$!
            fi
        else
            echo -e "${YELLOW}Creating virtual environment for Django backend...${NC}"
            if command -v uv &> /dev/null; then
                uv sync
                (unset VIRTUAL_ENV && uv run python manage.py runserver $BACKEND_PORT) &
                DJANGO_PID=$!
            else
                python -m venv .venv
                source .venv/bin/activate
                pip install -r requirements.txt
                python manage.py runserver $BACKEND_PORT &
                DJANGO_PID=$!
            fi
        fi
        
        cd ..
        
        # Wait for Django to start
        echo -e "${YELLOW}Waiting for Django to start...${NC}"
        for i in {1..30}; do
            if check_port $BACKEND_PORT; then
                echo -e "${GREEN}✓ Django backend started successfully on port $BACKEND_PORT${NC}"
                break
            fi
            sleep 1
        done
        
        if ! check_port $BACKEND_PORT; then
            echo -e "${RED}Failed to start Django backend${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Backend directory not found!${NC}"
        exit 1
    fi
fi

# Check and start Qdrant
if check_port $QDRANT_PORT; then
    echo -e "${GREEN}✓ Qdrant is already running on port $QDRANT_PORT${NC}"
else
    echo -e "${YELLOW}Qdrant is NOT running on port $QDRANT_PORT${NC}"
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed or not available${NC}"
        echo -e "${YELLOW}Please install Docker to run Qdrant${NC}"
        exit 1
    fi
    
    # Check if qdrant-thoth container exists
    if docker ps -a --format "table {{.Names}}" | grep -q "^qdrant-thoth$"; then
        echo -e "${YELLOW}Starting existing qdrant-thoth container...${NC}"
        docker start qdrant-thoth
        QDRANT_CONTAINER="qdrant-thoth"
    else
        echo -e "${YELLOW}Creating and starting new qdrant-thoth container...${NC}"
        docker run -d \
            --name qdrant-thoth \
            -p 6334:6333 \
            -v $(pwd)/qdrant_storage:/qdrant/storage:z \
            qdrant/qdrant
        QDRANT_CONTAINER="qdrant-thoth"
    fi
    
    # Wait for Qdrant to start
    echo -e "${YELLOW}Waiting for Qdrant to start...${NC}"
    for i in {1..30}; do
        if check_port $QDRANT_PORT; then
            echo -e "${GREEN}✓ Qdrant started successfully on port $QDRANT_PORT${NC}"
            break
        fi
        sleep 1
    done
    
    if ! check_port $QDRANT_PORT; then
        echo -e "${RED}Failed to start Qdrant${NC}"
        exit 1
    fi
fi

# Check and start SQL Generator (with cleanup)
echo -e "${YELLOW}Checking SQL Generator on port $SQL_GENERATOR_PORT...${NC}"

# Always cleanup existing SQL Generator processes first
cleanup_sql_generator

if check_port $SQL_GENERATOR_PORT; then
    echo -e "${YELLOW}Port $SQL_GENERATOR_PORT still in use, killing processes...${NC}"
    kill_port $SQL_GENERATOR_PORT
fi

echo -e "${YELLOW}Starting SQL Generator...${NC}"
# Ensure uv is available for the SQL Generator (it uses pyproject.toml/uv.lock)
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' is required to run the SQL Generator locally.${NC}"
    echo -e "${YELLOW}Install with:${NC} curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
cd "$SQL_GEN_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment for SQL Generator...${NC}"
    (unset VIRTUAL_ENV && uv sync)
else
    echo -e "${YELLOW}Updating SQL Generator dependencies...${NC}"
    (unset VIRTUAL_ENV && uv sync)
fi

# Start SQL Generator
(unset VIRTUAL_ENV && PORT=$SQL_GENERATOR_PORT uv run python main.py) &
SQL_GEN_PID=$!
cd ../..

# Wait for SQL Generator to start
echo -e "${YELLOW}Waiting for SQL Generator to start...${NC}"
for i in {1..30}; do
    if check_port $SQL_GENERATOR_PORT; then
        echo -e "${GREEN}✓ SQL Generator started successfully on port $SQL_GENERATOR_PORT${NC}"
        break
    fi
    sleep 1
done

if ! check_port $SQL_GENERATOR_PORT; then
    echo -e "${RED}Failed to start SQL Generator${NC}"
    exit 1
fi

# Check and start Frontend (Next.js)
echo -e "${YELLOW}Checking Frontend on port $FRONTEND_PORT...${NC}"
if check_port $FRONTEND_PORT; then
    echo -e "${GREEN}✓ Frontend is already running on port $FRONTEND_PORT${NC}"
else
    echo -e "${YELLOW}Frontend is NOT running on port $FRONTEND_PORT${NC}"
    echo -e "${YELLOW}Starting Frontend...${NC}"
    
    # Check if frontend directory exists
    if [ -d "frontend" ]; then
        cd frontend
        
        # Check if node_modules exists
        if [ ! -d "node_modules" ]; then
            # Ensure Node.js/npm is installed
            if ! command -v npm &> /dev/null; then
                echo -e "${RED}Error: npm is not installed. Please install Node.js (v20+) and retry.${NC}"
                exit 1
            fi
            echo -e "${YELLOW}Installing Frontend dependencies...${NC}"
            npm install
        fi
        
        # Start Frontend with specific port
        PORT=$FRONTEND_PORT npm run dev &
        FRONTEND_PID=$!
        cd ..
        
        # Wait for Frontend to start
        echo -e "${YELLOW}Waiting for Frontend to start...${NC}"
        for i in {1..30}; do
            if check_port $FRONTEND_PORT; then
                echo -e "${GREEN}✓ Frontend started successfully on port $FRONTEND_PORT${NC}"
                break
            fi
            sleep 1
        done
        
        if ! check_port $FRONTEND_PORT; then
            echo -e "${RED}Failed to start Frontend${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Frontend directory not found!${NC}"
        exit 1
    fi
fi

# Display service information
echo -e "\n${GREEN}All services started successfully!${NC}"
echo "==========================================="
echo -e "${BLUE}Service URLs:${NC}"
echo -e "   Frontend App:     ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
echo -e "   Backend Home:     ${GREEN}http://localhost:$BACKEND_PORT${NC}"
echo -e "   Django Admin:     ${GREEN}http://localhost:$BACKEND_PORT/admin${NC}"
echo -e "   SQL Generator:    ${GREEN}http://localhost:$SQL_GENERATOR_PORT${NC}"
echo -e "   API Docs:         ${GREEN}http://localhost:$SQL_GENERATOR_PORT/docs${NC}"
echo -e "   Qdrant API:       ${GREEN}http://localhost:$QDRANT_PORT${NC}"

# Function to handle cleanup
cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    
    # Stop Frontend
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}✓ Frontend stopped${NC}"
    fi
    
    # Stop SQL Generator
    if [ ! -z "$SQL_GEN_PID" ]; then
        kill $SQL_GEN_PID 2>/dev/null
        echo -e "${GREEN}✓ SQL Generator stopped${NC}"
    fi
    
    # Stop Django if we started it
    if [ ! -z "$DJANGO_PID" ]; then
        echo -e "${YELLOW}Stopping Django backend...${NC}"
        kill $DJANGO_PID 2>/dev/null
        echo -e "${GREEN}✓ Django backend stopped${NC}"
    fi
    
    # Ask about Qdrant container
    if [ ! -z "$QDRANT_CONTAINER" ]; then
        read -p "Stop Qdrant container? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker stop $QDRANT_CONTAINER
            echo -e "${GREEN}✓ Qdrant container stopped${NC}"
        else
            echo -e "${YELLOW}Qdrant container left running${NC}"
        fi
    fi
    
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# Set up trap to catch Ctrl+C
trap cleanup INT

echo -e "\n${BLUE}===========================================${NC}"
echo -e "${GREEN}All services are running. Press Ctrl+C to stop all services.${NC}"
echo -e "${BLUE}===========================================${NC}"

# Wait for services
wait