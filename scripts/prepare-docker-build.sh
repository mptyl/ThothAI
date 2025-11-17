#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Prepare Docker build on Windows/WSL by fixing common issues

echo "Preparing Docker build..."

# Fix line endings for all shell scripts
echo "Converting line endings to Unix format (LF)..."

# Find all .sh files and entrypoint scripts
find . -name "*.sh" -o -name "entrypoint*" | grep -v node_modules | grep -v .venv | while read file; do
    if [ -f "$file" ]; then
        # Check if file has CRLF line endings
        if file "$file" | grep -q "CRLF"; then
            echo "  Converting: $file"
            # Convert CRLF to LF
            sed -i 's/\r$//' "$file"
        fi
    fi
done

# Make all scripts executable
echo "Making scripts executable..."
find . -name "*.sh" -o -name "entrypoint*" | grep -v node_modules | grep -v .venv | xargs chmod +x 2>/dev/null

# Verify critical files exist
echo "Verifying critical files..."
CRITICAL_FILES=(
    "frontend/sql_generator/entrypoint-sql-generator.sh"
    "backend/entrypoint-backend.sh"
    "frontend/entrypoint-frontend.sh"
    "backend/scripts/start.sh"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file MISSING!"
    fi
done

echo ""
echo "Preparation complete!"
echo "Now run: docker-compose build --no-cache"