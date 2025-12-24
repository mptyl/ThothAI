#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Stop all Thoth UI services

echo "Stopping Thoth UI Services..."
echo "================================"

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
        echo "Port $port is now free"
    else
        echo "No processes found on port $port"
    fi
}

# Stop all services
echo "Cleaning up processes..."

# Kill SQL Generator processes
echo "Stopping SQL Generator (port 8001)..."
pkill -f "python.*main\.py" 2>/dev/null || true
pkill -f "sql_generator" 2>/dev/null || true
kill_port 8001

# Kill Next.js processes  
echo "Stopping Next.js Frontend (port 3000)..."
pkill -f "next.*dev" 2>/dev/null || true
pkill -f "npm.*run.*dev" 2>/dev/null || true
kill_port 3000

# Note: We don't kill Django backend as it might be used by other services
echo "Django Backend (port 8040) left running"

echo ""
echo "All Thoth UI services stopped!"
echo "Django backend may still be running on port 8040"