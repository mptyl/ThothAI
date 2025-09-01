#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# Script to upload new databases from local data/ directory to Docker volume
# Usage: ./scripts/upload_database.sh [database_name]
# If no database_name is provided, all databases in dev_databases will be synced

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if the backend container is running
if ! docker ps | grep -q thoth-backend; then
    print_error "thoth-backend container is not running. Please start the services first."
    print_info "Run: docker-compose up -d"
    exit 1
fi

# Get the database name from argument or sync all
DATABASE_NAME=$1

if [ -z "$DATABASE_NAME" ]; then
    print_info "No specific database provided. Syncing all databases in dev_databases..."
    
    # Check if dev_databases exists locally
    if [ ! -d "data/dev_databases" ]; then
        print_error "Directory data/dev_databases not found"
        exit 1
    fi
    
    # Copy all databases to the Docker volume
    print_info "Copying all databases to Docker volume..."
    docker exec thoth-backend mkdir -p /app/data/dev_databases
    
    # Use docker cp to copy the entire dev_databases directory
    docker cp data/dev_databases/. thoth-backend:/app/data/dev_databases/
    
    print_info "All databases uploaded successfully!"
    
else
    # Upload specific database
    print_info "Uploading database: $DATABASE_NAME"
    
    # Check if the database exists locally
    if [ ! -d "data/dev_databases/$DATABASE_NAME" ]; then
        print_error "Database directory not found: data/dev_databases/$DATABASE_NAME"
        print_info "Available databases:"
        ls -la data/dev_databases/ 2>/dev/null || echo "No databases found"
        exit 1
    fi
    
    # Create the target directory in Docker if it doesn't exist
    docker exec thoth-backend mkdir -p /app/data/dev_databases
    
    # Copy the specific database directory to Docker
    print_info "Copying $DATABASE_NAME to Docker volume..."
    docker cp "data/dev_databases/$DATABASE_NAME" thoth-backend:/app/data/dev_databases/
    
    print_info "Database $DATABASE_NAME uploaded successfully!"
fi

# Verify the upload
print_info "Verifying upload..."
echo "Contents of /app/data/dev_databases in Docker:"
docker exec thoth-backend ls -la /app/data/dev_databases/

# Check for dev.json file
if docker exec thoth-backend test -f /app/data/dev_databases/dev.json; then
    print_info "dev.json file found in Docker volume ✓"
else
    print_warning "dev.json file not found in Docker volume"
    print_info "You may need to copy it manually:"
    print_info "  docker cp data/dev_databases/dev.json thoth-backend:/app/data/dev_databases/"
fi

print_info "Upload complete!"
print_info "You can now use the uploaded database(s) in the application"

# Optional: Trigger evidence loading
read -p "Do you want to trigger evidence loading now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Triggering evidence loading..."
    docker exec thoth-backend python manage.py shell -c "
from thoth_ai_backend.preprocessing.upload_evidence import upload_to_qdrant
from thoth_core.models import SqlDatabase
# Get all databases or specific one
databases = SqlDatabase.objects.all()
for db in databases:
    print(f'Loading evidence for {db.name}...')
    try:
        upload_to_qdrant(db.id)
        print(f'Evidence loaded for {db.name}')
    except Exception as e:
        print(f'Error loading evidence for {db.name}: {e}')
"
    print_info "Evidence loading complete!"
fi