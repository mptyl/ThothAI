#!/bin/bash

# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Thoth UI Docker Run Script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}    Thoth UI Docker Run Script${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Docker is running${NC}"
}

# Function to check if images exist
check_images() {
    local missing_images=false
    
    echo -e "${BLUE}Checking Docker images...${NC}"
    
    if ! docker images | grep -q "thoth-ui"; then
        echo -e "${YELLOW}thoth-ui image not found${NC}"
        missing_images=true
    fi
    
    if ! docker images | grep -q "sql-generator"; then
        echo -e "${YELLOW}sql-generator image not found${NC}"
        missing_images=true
    fi
    
    if [ "$missing_images" = true ]; then
        echo -e "${YELLOW}Building missing images...${NC}"
        ./build.sh
    else
        echo -e "${GREEN}All images found${NC}"
    fi
}

# Function to check if services are already running
check_running_services() {
    local running_services=$(docker-compose ps --services --filter "status=running" 2>/dev/null)
    
    if [ -n "$running_services" ]; then
        echo -e "${YELLOW}Found running services:${NC}"
        echo "$running_services"
        echo ""
        read -p "Do you want to restart them? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Stopping existing services...${NC}"
            docker-compose down
            echo -e "${GREEN}Services stopped${NC}"
        else
            echo -e "${RED}Exiting. Please stop services manually with ./clean-docker.sh${NC}"
            exit 1
        fi
    fi
}

# Function to start services
start_services() {
    local MODE="production"
    local COMPOSE_FILE="docker-compose.yml"
    local DETACHED=""
    local SPECIFIC_SERVICE=""
    local FOLLOW_LOGS=""
    
    # Parse arguments
    for arg in "$@"; do
        case $arg in
            --dev)
                MODE="development"
                COMPOSE_FILE="docker-compose.dev.yml"
                echo -e "${YELLOW}Running in development mode${NC}"
                ;;
            --detached|-d)
                DETACHED="-d"
                echo -e "${YELLOW}Running in detached mode${NC}"
                ;;
            --ui-only)
                SPECIFIC_SERVICE="thoth-ui"
                echo -e "${YELLOW}Starting UI service only${NC}"
                ;;
            --sql-only)
                SPECIFIC_SERVICE="sql-generator"
                echo -e "${YELLOW}Starting SQL Generator service only${NC}"
                ;;
            --logs|-l)
                FOLLOW_LOGS="true"
                ;;
            --orchestrator)
                COMPOSE_FILE="docker-compose.orchestrator.yml"
                echo -e "${YELLOW}Running with orchestrator mode${NC}"
                ;;
            *)
                ;;
        esac
    done
    
    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo -e "${RED}$COMPOSE_FILE not found${NC}"
        exit 1
    fi
    
    echo ""
    echo -e "${BLUE}Starting services...${NC}"
    echo -e "  Mode: ${CYAN}$MODE${NC}"
    echo -e "  Compose file: ${CYAN}$COMPOSE_FILE${NC}"
    echo ""
    
    # Start services
    if [ -n "$SPECIFIC_SERVICE" ]; then
        docker-compose -f $COMPOSE_FILE up $DETACHED $SPECIFIC_SERVICE
    else
        docker-compose -f $COMPOSE_FILE up $DETACHED
    fi
    
    # Follow logs if requested and running detached
    if [ -n "$DETACHED" ] && [ -n "$FOLLOW_LOGS" ]; then
        echo ""
        echo -e "${BLUE}Following logs (Ctrl+C to stop)...${NC}"
        docker-compose -f $COMPOSE_FILE logs -f
    fi
}

# Function to display service status
display_status() {
    echo ""
    echo -e "${BLUE}Service Status:${NC}"
    docker-compose ps
    echo ""
    
    # Check service health
    echo -e "${BLUE}Service Health:${NC}"
    
    # Check UI
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 | grep -q "200\|302"; then
        echo -e "  ${GREEN}OK${NC} UI: http://localhost:3001"
    else
        echo -e "  ${YELLOW}STARTING${NC} UI: Starting up... (http://localhost:3001)"
    fi
    
    # Check SQL Generator
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8005/health 2>/dev/null | grep -q "200"; then
        echo -e "  ${GREEN}OK${NC} SQL Generator API: http://localhost:8005"
    else
        echo -e "  ${YELLOW}STARTING${NC} SQL Generator API: Starting up... (http://localhost:8005)"
    fi
    
    echo ""
}

# Function to display logs help
display_logs_help() {
    if [ -n "$DETACHED" ]; then
        echo -e "${BLUE}View logs:${NC}"
        echo -e "  All services: ${CYAN}docker-compose logs -f${NC}"
        echo -e "  UI only: ${CYAN}docker-compose logs -f thoth-ui${NC}"
        echo -e "  SQL Generator: ${CYAN}docker-compose logs -f sql-generator${NC}"
        echo ""
    fi
}

# Main execution
echo -e "${BLUE}Starting Thoth UI services...${NC}"
echo ""

# Check prerequisites
check_docker
check_images
check_running_services

# Start services
start_services "$@"

# If running detached, show status
if [ -n "$DETACHED" ]; then
    sleep 3  # Give services time to start
    display_status
    display_logs_help
    
    echo -e "${GREEN}==================================${NC}"
    echo -e "${GREEN}   Services started successfully!${NC}"
    echo -e "${GREEN}==================================${NC}"
    echo ""
    echo -e "${YELLOW}Quick commands:${NC}"
    echo -e "  Stop services: ${BLUE}./clean-docker.sh${NC}"
    echo -e "  View logs: ${BLUE}docker-compose logs -f${NC}"
    echo -e "  Service status: ${BLUE}docker-compose ps${NC}"
    echo ""
fi