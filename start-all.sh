#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Start all ThothAI services and run tests
# This script starts the frontend, SQL generator, and runs test queries

echo "Starting ThothAI Services with Testing..."
echo "========================================="

# Configuration
FRONTEND_DIR="frontend"
SQL_GEN_DIR="frontend/sql_generator"
TEST_OUTPUT_DIR="cs_test"

# Load environment variables from root .env.local
if [ -f .env.local ]; then
    echo -e "${GREEN}Loading environment from .env.local${NC}"
    export $(grep -v '^#' .env.local | xargs)
else
    echo -e "${RED}Error: .env.local not found in root directory${NC}"
    echo -e "${YELLOW}Please create .env.local from .env.template${NC}"
    exit 1
fi

# Port configuration from environment
FRONTEND_LOCAL_PORT=${FRONTEND_LOCAL_PORT:-3200}
SQL_GEN_LOCAL_PORT=${SQL_GENERATOR_LOCAL_PORT:-8180}
BACKEND_LOCAL_PORT=${BACKEND_LOCAL_PORT:-8200}
QDRANT_PORT=6334

# Global PIDs for cleanup
DJANGO_PID=""
QDRANT_CONTAINER=""
SQL_GEN_PID=""
NEXT_PID=""

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

# Create test output directory
create_test_directory() {
    if [ ! -d "$TEST_OUTPUT_DIR" ]; then
        echo -e "${GREEN}Creating test output directory: $TEST_OUTPUT_DIR${NC}"
        mkdir -p "$TEST_OUTPUT_DIR"
    else
        echo -e "${GREEN}Test output directory exists: $TEST_OUTPUT_DIR${NC}"
    fi
}

# Function to run test queries
run_test_queries() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local output_file="${TEST_OUTPUT_DIR}/test_results_${timestamp}.txt"
    
    echo -e "\n${BLUE}Running test queries...${NC}"
    echo "Test results will be saved to: $output_file"
    echo "===========================================" > "$output_file"
    echo "ThothAI SQL Generator Test Results" >> "$output_file"
    echo "Timestamp: $(date)" >> "$output_file"
    echo "===========================================" >> "$output_file"
    
    # Wait for services to be ready
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    sleep 5
    
    # Test queries
    local queries=(
        "How many schools are exclusively virtual?"
        "How many schools with an average score in Math greater than 400 in the SAT test are exclusively virtual?"
        "What are the top 5 schools by Math scores?"
        "Show me all charter schools with enrollment over 500 students"
    )
    
    for i in "${!queries[@]}"; do
        local question="${queries[$i]}"
        echo -e "\n${GREEN}Test $((i+1)): ${question}${NC}"
        echo -e "\n\nTest $((i+1)): ${question}" >> "$output_file"
        echo "----------------------------------------" >> "$output_file"
        
        # Make the curl request
        local response=$(curl -X POST "http://localhost:${SQL_GEN_LOCAL_PORT}/generate-sql" \
            -H "Content-Type: application/json" \
            -H "Accept: text/plain" \
            -d "{
                \"workspace_id\": 4,
                \"question\": \"${question}\",
                \"username\": \"marco\",
                \"functionality_level\": \"BASIC\",
                \"flags\": {
                    \"use_schema\": true,
                    \"use_examples\": true,
                    \"use_lsh\": true,
                    \"use_vector\": true
                }
            }" 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            echo "$response" >> "$output_file"
            echo -e "${GREEN}✓ Query executed successfully${NC}"
        else
            echo "ERROR: Failed to execute query" >> "$output_file"
            echo -e "${RED}✗ Query failed${NC}"
        fi
    done
    
    echo -e "\n${GREEN}Test results saved to: $output_file${NC}"
}

# Main script starts here
echo -e "${BLUE}ThothAI Service Startup Script${NC}"
echo "================================="

# Step 1: Check and start required services
echo -e "\n${YELLOW}Step 1: Checking and starting required services...${NC}"

# Check and start Django backend
if check_port $BACKEND_LOCAL_PORT; then
    echo -e "${GREEN}✓ Django backend is already running on port $BACKEND_LOCAL_PORT${NC}"
else
    echo -e "${YELLOW}Django backend is NOT running on port $BACKEND_LOCAL_PORT${NC}"
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
                uv run python manage.py runserver $BACKEND_LOCAL_PORT &
                DJANGO_PID=$!
            else
                # Fallback to regular Python
                echo -e "${GREEN}Starting Django with Python...${NC}"
                source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
                python manage.py runserver $BACKEND_LOCAL_PORT &
                DJANGO_PID=$!
            fi
        else
            echo -e "${YELLOW}Creating virtual environment for Django backend...${NC}"
            if command -v uv &> /dev/null; then
                uv sync
                uv run python manage.py runserver $BACKEND_LOCAL_PORT &
                DJANGO_PID=$!
            else
                python -m venv .venv
                source .venv/bin/activate
                pip install -r requirements.txt
                python manage.py runserver $BACKEND_LOCAL_PORT &
                DJANGO_PID=$!
            fi
        fi
        
        cd ..
        
        # Wait for Django to start
        echo -e "${YELLOW}Waiting for Django to start...${NC}"
        for i in {1..30}; do
            if check_port $BACKEND_LOCAL_PORT; then
                echo -e "${GREEN}✓ Django backend started successfully on port $BACKEND_LOCAL_PORT${NC}"
                break
            fi
            sleep 1
        done
        
        if ! check_port $BACKEND_LOCAL_PORT; then
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
            -p 6334:6334 \
            -p 6333:6333 \
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

# Step 2: Create test directory
echo -e "\n${YELLOW}Step 2: Setting up test environment...${NC}"
create_test_directory

# Step 3: Check and prepare frontend environment
echo -e "\n${YELLOW}Step 3: Preparing frontend environment...${NC}"

cd "$FRONTEND_DIR"

# Frontend will use environment variables from root .env.local
echo -e "${GREEN}Frontend will use environment from root .env.local${NC}"

# Step 4: Clean up existing processes
echo -e "\n${YELLOW}Step 4: Cleaning up existing processes...${NC}"
cleanup_sql_generator

# Check and clean ports
if check_port $FRONTEND_LOCAL_PORT; then
    read -p "Port $FRONTEND_LOCAL_PORT is in use. Kill processes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill_port $FRONTEND_LOCAL_PORT
    else
        echo -e "${RED}Cannot start - port $FRONTEND_LOCAL_PORT is in use${NC}"
        exit 1
    fi
fi

if check_port $SQL_GEN_LOCAL_PORT; then
    read -p "Port $SQL_GEN_LOCAL_PORT is in use. Kill processes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill_port $SQL_GEN_LOCAL_PORT
    else
        echo -e "${RED}Cannot start - port $SQL_GEN_LOCAL_PORT is in use${NC}"
        exit 1
    fi
fi

# Step 5: Install dependencies
echo -e "\n${YELLOW}Step 5: Installing dependencies...${NC}"
npm install

# Step 6: Setup SQL Generator
echo -e "\n${YELLOW}Step 6: Setting up SQL Generator...${NC}"
cd sql_generator

# Check if uv virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating UV virtual environment...${NC}"
    uv sync --isolated
else
    echo -e "${YELLOW}Updating UV dependencies...${NC}"
    uv sync --isolated
fi

# Step 7: Start services
echo -e "\n${YELLOW}Step 7: Starting services...${NC}"

# Start SQL Generator
echo -e "${GREEN}Starting SQL Generator on port $SQL_GEN_LOCAL_PORT...${NC}"
PORT=$SQL_GEN_LOCAL_PORT uv run python main.py &
SQL_GEN_PID=$!

cd ../..

# Start Frontend
echo -e "${GREEN}Starting Next.js frontend on port $FRONTEND_LOCAL_PORT...${NC}"
cd "$FRONTEND_DIR"
PORT=$FRONTEND_LOCAL_PORT npm run dev &
NEXT_PID=$!

cd ..

# Step 8: Display service information
echo -e "\n${GREEN}All services started!${NC}"
echo "==========================================="
echo -e "${BLUE}Service URLs:${NC}"
echo -e "   Frontend:      ${GREEN}http://localhost:$FRONTEND_LOCAL_PORT${NC}"
echo -e "   SQL Generator: ${GREEN}http://localhost:$SQL_GEN_LOCAL_PORT${NC}"
echo -e "   API Docs:      ${GREEN}http://localhost:$SQL_GEN_LOCAL_PORT/docs${NC}"
echo -e "   Django Admin:  ${GREEN}http://localhost:$BACKEND_LOCAL_PORT/admin${NC}"
echo -e "   Qdrant UI:     ${GREEN}http://localhost:$QDRANT_PORT/dashboard${NC}"

# Check for Logfire token
if [ -f "$FRONTEND_DIR/.env.local" ]; then
    LOGFIRE_TOKEN=$(grep "^LOGFIRE_TOKEN=" "$FRONTEND_DIR/.env.local" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    if [ ! -z "$LOGFIRE_TOKEN" ] && [ "$LOGFIRE_TOKEN" != "" ] && [ "$LOGFIRE_TOKEN" != "put-your-api-key-here" ]; then
        echo -e "\n${BLUE}Logfire Dashboard:${NC}"
        echo -e "   ${GREEN}https://logfire.pydantic.dev/${NC}"
    fi
fi

# Step 9: Run test queries
echo -e "\n${YELLOW}Step 9: Running test queries...${NC}"
run_test_queries

# Function to handle cleanup
cleanup() {
    echo -e "\n${YELLOW}Stopping services...${NC}"
    
    # Stop SQL Generator
    if [ ! -z "$SQL_GEN_PID" ]; then
        kill $SQL_GEN_PID 2>/dev/null
        echo -e "${GREEN}✓ SQL Generator stopped${NC}"
    fi
    
    # Stop Frontend
    if [ ! -z "$NEXT_PID" ]; then
        kill $NEXT_PID 2>/dev/null
        echo -e "${GREEN}✓ Frontend stopped${NC}"
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
echo -e "${GREEN}Services are running. Press Ctrl+C to stop all services.${NC}"
echo -e "${BLUE}===========================================${NC}"

# Wait for services
wait