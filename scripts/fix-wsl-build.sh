#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Script to fix common Windows/WSL Docker build issues

echo "Fixing potential Windows/WSL build issues..."

# Ensure line endings are correct (LF not CRLF)
if command -v dos2unix > /dev/null 2>&1; then
    echo "Converting line endings to Unix format..."
    find frontend -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" -o -name "*.js" | xargs dos2unix 2>/dev/null || true
else
    echo "dos2unix not found. Install it with: sudo apt-get install dos2unix"
fi

# Check if lib/contexts directory exists
if [ ! -d "frontend/lib/contexts" ]; then
    echo "ERROR: frontend/lib/contexts directory not found!"
    exit 1
fi

# Check if workspace-context.tsx exists
if [ ! -f "frontend/lib/contexts/workspace-context.tsx" ]; then
    echo "ERROR: workspace-context.tsx not found!"
    exit 1
fi

echo "Checking file permissions..."
# Ensure files are readable
chmod -R a+r frontend/lib

echo "File structure looks correct."
echo ""
echo "Files in frontend/lib/contexts:"
ls -la frontend/lib/contexts/

echo ""
echo "Now try building again with:"
echo "  docker-compose build frontend"
echo ""
echo "If the issue persists, try:"
echo "  1. docker-compose down"
echo "  2. docker system prune -f"
echo "  3. docker-compose build --no-cache frontend"