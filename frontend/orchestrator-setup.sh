#!/bin/bash

# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Thoth Orchestrator Setup Script
# Sets up environment files and runs the complete Thoth ecosystem

set -e

echo "Thoth Orchestrator Setup"
echo "============================="

# Check if we're in the right directory
if [ ! -f "docker-compose.orchestrator.yml" ]; then
    echo "Error: This script must be run from the thoth_ui directory"
    echo "   Please cd to the directory containing docker-compose.orchestrator.yml"
    exit 1
fi

# Function to check if file exists and is not empty
check_env_file() {
    local file=$1
    local description=$2
    
    if [ ! -f "$file" ]; then
        echo "$description not found: $file"
        return 1
    elif [ ! -s "$file" ]; then
        echo "$description is empty: $file"
        return 1
    else
        echo "$description found: $file"
        return 0
    fi
}

# Check environment files
echo ""
echo "Checking Environment Files..."
echo "---------------------------------"

# Check thoth_ui environment
if check_env_file ".env.docker" "Thoth UI environment file"; then
    UI_ENV_OK=true
else
    UI_ENV_OK=false
fi

# Check thoth_be environment
if check_env_file "../thoth_be/_env" "Thoth Backend environment file"; then
    BE_ENV_OK=true
else
    BE_ENV_OK=false
    echo ""
    echo "Setting up Thoth Backend environment file..."
    
    if [ -f "../thoth_be/_env.template" ]; then
        cp "../thoth_be/_env.template" "../thoth_be/_env"
        echo "Created _env from template: ../thoth_be/_env"
        echo "Please edit ../thoth_be/_env and add your API keys before running the orchestrator"
    else
        echo "Error: Template file not found: ../thoth_be/_env.template"
        echo "   Please create ../thoth_be/_env manually with the required environment variables"
        exit 1
    fi
fi

# Check Docker network
echo ""
echo "Checking Docker Network..."
echo "-----------------------------"

if docker network inspect thothnet >/dev/null 2>&1; then
    echo "Network 'thothnet' already exists"
else
    echo "Creating Docker network 'thothnet'..."
    docker network create thothnet
    echo "Network 'thothnet' created"
fi

# Summary
echo ""
echo "Setup Summary"
echo "=================="
echo "Thoth UI Environment: $([ "$UI_ENV_OK" = true ] && echo "Ready" || echo "Needs setup")"
echo "Thoth Backend Environment: $([ "$BE_ENV_OK" = true ] && echo "Ready" || echo "Check API keys")"
echo "Docker Network: Ready"
echo ""

if [ "$UI_ENV_OK" = true ] && [ "$BE_ENV_OK" = true ]; then
    echo "All systems ready! You can now run:"
    echo "   docker-compose -f docker-compose.orchestrator.yml up --build"
    echo ""
    echo "Or run this script with 'start' to launch automatically:"
    echo "   ./orchestrator-setup.sh start"
else
    echo "Please fix the environment files before running the orchestrator"
    exit 1
fi

# Auto-start if requested
if [ "$1" = "start" ]; then
    echo ""
    echo "Starting Thoth Orchestrator..."
    echo "================================="
    docker-compose -f docker-compose.orchestrator.yml up --build
fi