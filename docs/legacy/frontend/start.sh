#!/bin/bash

# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Thoth UI Start Script

echo "Starting Thoth UI..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js 18+ and try again."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "npm is not installed. Please install npm and try again."
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "Creating .env.local from template..."
    cp .env.local.template .env.local
    echo "Please edit .env.local to configure your DJANGO_SERVER URL"
fi

# Start development server
echo "Starting development server on http://localhost:3000"
echo "Make sure your Django backend is running on the configured DJANGO_SERVER URL"
echo ""
npm run dev