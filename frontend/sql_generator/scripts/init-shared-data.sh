#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# Since we now use thoth-shared-data volume mounted at /app/data,
# this script only needs to verify the data is accessible
echo "SQL Generator: Checking shared data volume..."

if [ -f "/app/data/dev_databases/dev.json" ]; then
    echo "SQL Generator: Shared data volume is properly mounted and contains dev.json"
    echo "SQL Generator: Data directory contents:"
    ls -la /app/data/dev_databases/ | head -5
else
    echo "SQL Generator: WARNING - dev.json not found in shared data volume"
    echo "SQL Generator: Available at /app/data:"
    ls -la /app/data/ 2>/dev/null || echo "Data directory not accessible"
fi

# No symlinks needed - /app/data is the mounted volume