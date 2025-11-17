#!/bin/bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Fix line endings for shell scripts (CRLF -> LF)

echo "Fixing line endings for shell scripts..."

# Find all .sh files and convert line endings
find . -name "*.sh" -type f | while read file; do
    if command -v dos2unix > /dev/null 2>&1; then
        echo "Converting: $file"
        dos2unix "$file" 2>/dev/null
    else
        # Fallback method using sed
        echo "Converting (sed): $file"
        sed -i.bak 's/\r$//' "$file" && rm "${file}.bak"
    fi
done

echo "Line endings fixed!"
echo ""
echo "Now rebuild the containers:"
echo "  docker-compose build --no-cache"
echo "  docker-compose up"