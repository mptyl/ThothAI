#!/bin/bash

# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Thoth UI Docker Clean Script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}   Thoth UI Docker Clean Script${NC}"
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

# Function to stop services
stop_services() {
    echo -e "${BLUE}🛑 Stopping services...${NC}"
    
    # Check which compose files exist and stop services
    if [ -f "docker-compose.yml" ]; then
        docker-compose down 2>/dev/null || true
    fi
    
    if [ -f "docker-compose.dev.yml" ]; then
        docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    fi
    
    if [ -f "docker-compose.orchestrator.yml" ]; then
        docker-compose -f docker-compose.orchestrator.yml down 2>/dev/null || true
    fi
    
    echo -e "${GREEN}Services stopped${NC}"
}

# Function to clean containers
clean_containers() {
    echo -e "${BLUE}Cleaning containers...${NC}"
    
    # Remove Thoth UI containers
    local containers=$(docker ps -a --filter "name=thoth-ui" --filter "name=thoth-sql-generator" -q)
    
    if [ -n "$containers" ]; then
        echo "Removing containers:"
        docker rm -f $containers 2>/dev/null || true
        echo -e "${GREEN}Containers removed${NC}"
    else
        echo -e "${YELLOW}No containers to remove${NC}"
    fi
}

# Function to clean images
clean_images() {
    if [[ "$*" == *"--images"* ]] || [[ "$*" == *"--all"* ]]; then
        echo -e "${BLUE}Cleaning images...${NC}"
        
        # Find and remove Thoth UI images
        local images=$(docker images | grep -E "thoth-ui|sql-generator" | awk '{print $3}')
        
        if [ -n "$images" ]; then
            echo "Removing images:"
            echo "$images" | xargs docker rmi -f 2>/dev/null || true
            echo -e "${GREEN}Images removed${NC}"
        else
            echo -e "${YELLOW}No images to remove${NC}"
        fi
    fi
}

# Function to clean volumes
clean_volumes() {
    if [[ "$*" == *"--volumes"* ]] || [[ "$*" == *"--all"* ]]; then
        echo -e "${BLUE}Cleaning volumes...${NC}"
        
        # Remove Thoth UI volumes
        local volumes=$(docker volume ls --filter "name=thoth_ui" -q)
        
        if [ -n "$volumes" ]; then
            echo "Removing volumes:"
            echo "$volumes" | xargs docker volume rm 2>/dev/null || true
            echo -e "${GREEN}Volumes removed${NC}"
        else
            echo -e "${YELLOW}No volumes to remove${NC}"
        fi
    fi
}

# Function to clean networks
clean_networks() {
    if [[ "$*" == *"--network"* ]] || [[ "$*" == *"--all"* ]]; then
        echo -e "${BLUE}Cleaning networks...${NC}"
        
        # Check if network is in use
        local network_in_use=$(docker network inspect thothnet 2>/dev/null | grep -c "Containers" || echo "0")
        
        if [ "$network_in_use" -eq "0" ]; then
            docker network rm thothnet 2>/dev/null || true
            echo -e "${GREEN}Network removed${NC}"
        else
            echo -e "${YELLOW}Network 'thothnet' is still in use by other services${NC}"
        fi
    fi
}

# Function to prune system
prune_system() {
    if [[ "$*" == *"--prune"* ]]; then
        echo -e "${BLUE}Pruning Docker system...${NC}"
        docker system prune -f
        echo -e "${GREEN}System pruned${NC}"
    fi
}

# Function to clean buildx cache
clean_buildx_cache() {
    if [[ "$*" == *"--cache"* ]] || [[ "$*" == *"--all"* ]]; then
        echo -e "${BLUE}Cleaning Docker buildx cache...${NC}"
        
        # Remove buildx cache directories
        rm -rf /tmp/.buildx-cache* 2>/dev/null
        rm -rf /tmp/.docker-cache* 2>/dev/null
        
        # Remove buildx builders
        docker buildx ls | grep -v "default" | awk '{print $1}' | xargs -r docker buildx rm 2>/dev/null
        
        # Prune build cache
        docker builder prune -af 2>/dev/null
        docker buildx prune -af 2>/dev/null
        
        echo -e "${GREEN}Build cache removed${NC}"
        echo -e "${YELLOW}Next build will take longer (no cache)${NC}"
    fi
}

# Function to display cleanup summary
display_summary() {
    echo ""
    echo -e "${BLUE}Cleanup Summary:${NC}"
    echo -e "  ${GREEN}OK${NC} Services stopped"
    echo -e "  ${GREEN}OK${NC} Containers removed"
    
    if [[ "$*" == *"--images"* ]] || [[ "$*" == *"--all"* ]]; then
        echo -e "  ${GREEN}OK${NC} Images removed"
    fi
    
    if [[ "$*" == *"--volumes"* ]] || [[ "$*" == *"--all"* ]]; then
        echo -e "  ${GREEN}OK${NC} Volumes removed"
    fi
    
    if [[ "$*" == *"--network"* ]] || [[ "$*" == *"--all"* ]]; then
        echo -e "  ${GREEN}OK${NC} Network cleanup attempted"
    fi
    
    if [[ "$*" == *"--prune"* ]]; then
        echo -e "  ${GREEN}OK${NC} System pruned"
    fi
    
    echo ""
    
    # Show remaining Docker resources
    echo -e "${BLUE}Remaining Docker resources:${NC}"
    echo -e "  Containers: $(docker ps -a | wc -l | xargs -I {} echo "{} - 1" | bc)"
    echo -e "  Images: $(docker images | wc -l | xargs -I {} echo "{} - 1" | bc)"
    echo -e "  Volumes: $(docker volume ls | wc -l | xargs -I {} echo "{} - 1" | bc)"
    echo ""
}

# Function to display help
display_help() {
    echo -e "${BLUE}Usage:${NC} ./clean-docker.sh [OPTIONS]"
    echo ""
    echo -e "${BLUE}Options:${NC}"
    echo -e "  ${GREEN}(none)${NC}       Stop services and remove containers only"
    echo -e "  ${GREEN}--images${NC}     Also remove Docker images"
    echo -e "  ${GREEN}--volumes${NC}    Also remove Docker volumes"
    echo -e "  ${GREEN}--network${NC}    Also remove the thothnet network"
    echo -e "  ${GREEN}--all${NC}        Remove everything (containers, images, volumes, network)"
    echo -e "  ${GREEN}--prune${NC}      Also run Docker system prune"
    echo -e "  ${GREEN}--help${NC}       Display this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  ./clean-docker.sh                # Basic cleanup"
    echo -e "  ./clean-docker.sh --images       # Also remove images"
    echo -e "  ./clean-docker.sh --all          # Complete cleanup"
    echo -e "  ./clean-docker.sh --all --prune  # Complete cleanup + system prune"
    echo ""
}

# Main execution

# Check for help flag
if [[ "$*" == *"--help"* ]]; then
    display_help
    exit 0
fi

echo -e "${BLUE}Starting cleanup process...${NC}"
echo ""

# Confirmation for destructive operations
if [[ "$*" == *"--all"* ]] || [[ "$*" == *"--volumes"* ]]; then
    echo -e "${YELLOW}Warning: This will remove Docker volumes (potential data loss)${NC}"
    read -p "Are you sure you want to continue? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Cleanup cancelled${NC}"
        exit 1
    fi
fi

# Check Docker
check_docker

# Perform cleanup
stop_services
clean_containers
clean_images "$@"
clean_volumes "$@"
clean_networks "$@"
prune_system "$@"

# Clean buildx cache if requested
clean_buildx_cache "$@"

# Display summary
display_summary "$@"

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}   Cleanup completed successfully!${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""

# Show next steps based on what was cleaned
if [[ "$*" == *"--images"* ]] || [[ "$*" == *"--all"* ]]; then
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  1. Run ${BLUE}./build.sh${NC} to rebuild images"
    echo -e "  2. Run ${BLUE}./run.sh${NC} to start services"
else
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  Run ${BLUE}./run.sh${NC} to restart services"
fi
echo ""