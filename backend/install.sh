#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# ThothAI Interactive Installer with FastAPI
# Allows database selection and manages both backend and UI containers

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================="
echo "    ThothAI Interactive Installer"
echo "===================================${NC}"
echo ""

# Check if we are in the correct directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}[ERROR] pyproject.toml not found in current directory"
    echo "   Make sure you are in the thoth_be root directory${NC}"
    exit 1
fi

# Check if uv is installed
echo -e "${BLUE}[INFO] Checking uv installation...${NC}"
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}[WARNING] uv not found. Installing uv...${NC}"
    
    # Install uv based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows (Git Bash / Cygwin)
        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    else
        echo -e "${RED}[ERROR] Unsupported OS. Please install uv manually from https://github.com/astral-sh/uv${NC}"
        exit 1
    fi
    
    # Add to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"
    
    # Verify installation
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}[ERROR] Failed to install uv. Please install manually.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}[SUCCESS] uv installed successfully${NC}"
else
    echo -e "${GREEN}[SUCCESS] uv is already installed${NC}"
fi

# Install Python dependencies
echo ""
echo -e "${BLUE}📚 Installing Python dependencies...${NC}"
uv sync --extra dev

if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Failed to install dependencies${NC}"
    exit 1
fi

echo -e "${GREEN}[SUCCESS] Dependencies installed${NC}"

# Check if _env file exists, create from template if not
if [ ! -f "_env" ]; then
    echo ""
    echo -e "${YELLOW}📝 Creating _env file from template...${NC}"
    
    if [ -f "_env.template" ]; then
        cp _env.template _env
        echo -e "${GREEN}[SUCCESS] _env file created from template${NC}"
        echo -e "${YELLOW}[WARNING] Please edit _env file and add your API keys${NC}"
    else
        echo -e "${RED}[ERROR] _env.template not found. Please create _env file manually.${NC}"
        exit 1
    fi
fi

# Check if Docker is installed
echo ""
echo -e "${BLUE}🐳 Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker is not installed. Please install Docker Desktop first.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}[ERROR] Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

echo -e "${GREEN}[SUCCESS] Docker is installed and running${NC}"

# Setup Docker network and volumes
echo ""
echo -e "${BLUE}[INFO] Setting up Docker network and volumes...${NC}"

# Create network if not exists
if ! docker network ls | grep -q "thothnet"; then
    docker network create thothnet
    echo -e "${GREEN}[SUCCESS] Created Docker network: thothnet${NC}"
else
    echo "✓ Docker network thothnet already exists"
fi

# Create shared volume if not exists
if ! docker volume ls | grep -q "thoth-shared-data"; then
    docker volume create thoth-shared-data
    echo -e "${GREEN}[SUCCESS] Created Docker volume: thoth-shared-data${NC}"
else
    echo "✓ Docker volume thoth-shared-data already exists"
fi

# Check if port 8199 is already in use
echo ""
echo -e "${BLUE}🔍 Checking if port 8199 is available...${NC}"

# Function to check port on different OS
check_port() {
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # macOS and Linux
        if lsof -Pi :8199 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            return 0  # Port is in use
        else
            return 1  # Port is free
        fi
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows
        if netstat -an | grep -q ":8199.*LISTENING"; then
            return 0  # Port is in use
        else
            return 1  # Port is free
        fi
    else
        # Fallback: try to bind to the port with Python
        if uv run python -c "import socket; s=socket.socket(); s.bind(('',8199)); s.close()" 2>/dev/null; then
            return 1  # Port is free
        else
            return 0  # Port is in use
        fi
    fi
}

if check_port; then
    echo -e "${RED}[ERROR] Port 8199 is already in use!${NC}"
    echo ""
    echo -e "${YELLOW}This could be because:${NC}"
    echo "  • Another instance of the installer is already running"
    echo "  • Another application is using port 8199"
    echo ""
    echo -e "${CYAN}To fix this issue:${NC}"
    echo "  1. Close any other instance of the ThothAI installer"
    echo "  2. Or stop the application using port 8199"
    echo ""
    
    # Try to identify what's using the port
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo -e "${BLUE}Process using port 8199:${NC}"
        lsof -i :8199 2>/dev/null | grep LISTEN || echo "  Unable to identify process"
        echo ""
        echo -e "${YELLOW}To kill the process manually, run:${NC}"
        echo "  kill -9 \$(lsof -Pi :8199 -sTCP:LISTEN -t)"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo -e "${BLUE}Process using port 8199:${NC}"
        netstat -ano | grep :8199 | grep LISTENING || echo "  Unable to identify process"
    fi
    
    echo ""
    echo -e "${YELLOW}Do you want to try to automatically stop it? (y/N)${NC}"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Attempting to stop the process...${NC}"
        if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # First try without sudo
            if kill -9 $(lsof -Pi :8199 -sTCP:LISTEN -t) 2>/dev/null; then
                echo -e "${GREEN}Process stopped successfully${NC}"
            else
                echo -e "${YELLOW}Failed to stop process (might need elevated permissions)${NC}"
                echo ""
                echo -e "${CYAN}You can try one of the following:${NC}"
                echo "  1. Run with sudo: sudo kill -9 \$(lsof -Pi :8199 -sTCP:LISTEN -t)"
                echo "  2. Or restart the installer with: sudo ./install.sh"
                echo ""
                echo -e "${YELLOW}Would you like to try with sudo? (y/N)${NC}"
                read -r sudo_response
                
                if [[ "$sudo_response" =~ ^[Yy]$ ]]; then
                    echo -e "${YELLOW}Running with sudo (you may be prompted for password)...${NC}"
                    sudo kill -9 $(lsof -Pi :8199 -sTCP:LISTEN -t) 2>/dev/null && echo -e "${GREEN}Process stopped with sudo${NC}" || echo -e "${RED}Failed even with sudo${NC}"
                fi
            fi
        else
            echo -e "${RED}Automatic stop not supported on Windows. Please stop it manually.${NC}"
            exit 1
        fi
        sleep 2
        
        # Check again
        if check_port; then
            echo -e "${RED}Port 8199 is still in use.${NC}"
            echo ""
            echo -e "${YELLOW}The installer couldn't free the port automatically.${NC}"
            echo -e "${CYAN}Please manually stop the process using port 8199 and run the installer again.${NC}"
            echo ""
            echo -e "${BLUE}Tip: You can find and stop it with:${NC}"
            if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
                echo "  sudo kill -9 \$(lsof -Pi :8199 -sTCP:LISTEN -t)"
            fi
            exit 1
        fi
    else
        echo -e "${RED}Installation cancelled. Please free port 8199 and try again.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}[SUCCESS] Port 8199 is available${NC}"

# Start the FastAPI installer
echo ""
echo -e "${CYAN}[INFO] Starting interactive database configuration...${NC}"
echo -e "${BLUE}   The installer will open in your browser${NC}"
echo ""

# Create a log file for debugging
LOG_FILE="/tmp/thoth_installer_$(date +%Y%m%d_%H%M%S).log"
echo -e "${YELLOW}📝 Log file: $LOG_FILE${NC}"

# Start the FastAPI server in background with logging
uv run python installer_main.py > "$LOG_FILE" 2>&1 &
INSTALLER_PID=$!

# Wait for server to start
sleep 3

# Check if server is running
if ! kill -0 $INSTALLER_PID 2>/dev/null; then
    echo -e "${RED}[ERROR] Failed to start installer server${NC}"
    echo -e "${RED}Error output:${NC}"
    cat "$LOG_FILE"
    echo ""
    echo -e "${YELLOW}Press Enter to exit...${NC}"
    read
    exit 1
fi

# Try to open browser
echo -e "${GREEN}✨ Opening installer in browser...${NC}"
echo ""

# Detect OS and open browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "http://localhost:8199" 2>/dev/null || true
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open "http://localhost:8199" 2>/dev/null || true
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows
    start "http://localhost:8199" 2>/dev/null || true
fi

echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                          ║${NC}"
echo -e "${CYAN}║  ${YELLOW}📌 Installer is running at: ${GREEN}http://localhost:8199${CYAN}      ║${NC}"
echo -e "${CYAN}║                                                          ║${NC}"
echo -e "${CYAN}║  ${BLUE}1. Select your SQL databases (SQLite always included)${CYAN}   ║${NC}"
echo -e "${CYAN}║  ${BLUE}2. Click 'Deploy Backend' to start thoth_be${CYAN}            ║${NC}"
echo -e "${CYAN}║  ${BLUE}3. Click 'Deploy Frontend' to start thoth_ui${CYAN}           ║${NC}"
echo -e "${CYAN}║  ${BLUE}4. Click 'Shutdown Installer' when done${CYAN}                ║${NC}"
echo -e "${CYAN}║                                                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the installer${NC}"
echo ""

# Wait for installer to complete or user interrupt
wait $INSTALLER_PID

echo ""
echo -e "${GREEN}[SUCCESS] Installation process completed!${NC}"
echo ""
echo -e "${BLUE}📍 Access points:${NC}"
echo "  • Backend API:  http://localhost:8040"
echo "  • Admin panel:  http://localhost:8040/admin"
echo "  • Frontend UI:  http://localhost:3001 (if deployed)"
echo "  • Qdrant:       http://localhost:6333/dashboard"
echo ""
echo -e "${YELLOW}[TIP] To stop services: docker compose down${NC}"