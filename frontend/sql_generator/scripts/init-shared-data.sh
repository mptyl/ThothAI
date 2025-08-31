#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# Initialize shared data from static copy if needed
if [ ! -d "/app/shared_data/dev_databases" ]; then
    echo "SQL Generator: Initializing shared data from static copy..."
    cp -r /app/data_static/* /app/shared_data/ 2>/dev/null || true
    echo "SQL Generator: Shared data initialization complete."
fi

# Create symlink for backward compatibility
if [ ! -L "/app/data" ]; then
    echo "SQL Generator: Creating symlink for backward compatibility..."
    rm -rf /app/data 2>/dev/null || true
    ln -sfn /app/shared_data /app/data
    echo "SQL Generator: Symlink created: /app/data -> /app/shared_data"
fi