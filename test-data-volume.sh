#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

echo "===== Testing Data Volume Configuration ====="
echo ""

# Step 1: Stop all services
echo "Step 1: Stopping all services..."
docker-compose down

# Step 2: Remove the shared volume if it exists
echo ""
echo "Step 2: Removing existing shared volume..."
docker volume rm thoth-shared-data 2>/dev/null || echo "Volume didn't exist or couldn't be removed"

# Step 3: Build images with data included
echo ""
echo "Step 3: Building images with embedded data..."
docker-compose --profile init build --no-cache init-data
docker-compose build --no-cache backend sql-generator

# Step 4: Initialize the shared volume
echo ""
echo "Step 4: Initializing shared data volume..."
docker-compose --profile init up init-data

# Step 5: Start services
echo ""
echo "Step 5: Starting services..."
docker-compose up -d backend sql-generator

# Step 6: Wait for services to be ready
echo ""
echo "Step 6: Waiting for services to be ready..."
sleep 10

# Step 7: Verify data is accessible
echo ""
echo "Step 7: Verifying data is accessible..."

echo "Checking backend container:"
docker exec thoth-backend ls -la /app/data 2>/dev/null || echo "Failed to list /app/data in backend"
docker exec thoth-backend ls -la /app/shared_data 2>/dev/null || echo "Failed to list /app/shared_data in backend"

echo ""
echo "Checking sql-generator container:"
docker exec thoth-sql-generator ls -la /app/data 2>/dev/null || echo "Failed to list /app/data in sql-generator"
docker exec thoth-sql-generator ls -la /app/shared_data 2>/dev/null || echo "Failed to list /app/shared_data in sql-generator"

echo ""
echo "Checking if db.sqlite3 is accessible:"
docker exec thoth-backend ls -la /app/data/db.sqlite3 2>/dev/null && echo "✓ Backend can access db.sqlite3" || echo "✗ Backend cannot access db.sqlite3"
docker exec thoth-sql-generator ls -la /app/data/db.sqlite3 2>/dev/null && echo "✓ SQL Generator can access db.sqlite3" || echo "✗ SQL Generator cannot access db.sqlite3"

echo ""
echo "===== Test Complete ====="