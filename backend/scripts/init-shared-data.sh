#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# Initialize the thoth-shared-data volume on first run
# Check if the volume is properly initialized (dev.json exists)
if [ ! -f "/app/data/dev_databases/dev.json" ]; then
    echo "Initializing thoth-shared-data volume with data from /app/data_temp..."
    
    # Copy all data from the temporary directory to the volume
    if [ -d "/app/data_temp" ]; then
        # Use cp with force and preserve to ensure all files are copied
        cp -rf /app/data_temp/. /app/data/ 2>/dev/null || true
        echo "Data copied successfully to /app/data"
        
        # Remove the symlink that's not needed in Docker
        if [ -L "/app/data/shared_data" ]; then
            rm -f /app/data/shared_data
            echo "Removed unnecessary shared_data symlink"
        fi
        
        # List what was copied for verification
        echo "Initialized with:"
        ls -la /app/data/
        
        # Verify dev.json was copied
        if [ -f "/app/data/dev_databases/dev.json" ]; then
            echo "SUCCESS: dev.json copied successfully"
            ls -la /app/data/dev_databases/ | head -5
        else
            echo "ERROR: dev.json was not copied!"
            echo "Contents of /app/data:"
            find /app/data -type f -name "*.json" 2>/dev/null || true
        fi
        
        # Remove the temporary directory to save space
        rm -rf /app/data_temp
        echo "Temporary data directory removed"
    else
        echo "Warning: /app/data_temp not found, volume initialized empty"
    fi
else
    echo "Volume already initialized, skipping data copy"
    
    # Clean up temporary directory if it still exists
    if [ -d "/app/data_temp" ]; then
        rm -rf /app/data_temp
        echo "Cleaned up temporary data directory"
    fi
fi

echo "Backend database is in separate volume at /app/backend_db"

# Final verification that data persists
if [ -f "/app/data/dev_databases/dev.json" ]; then
    echo "VERIFICATION: dev.json is present in /app/data/dev_databases/"
    echo "File size: $(ls -lh /app/data/dev_databases/dev.json | awk '{print $5}')"
else
    echo "WARNING: dev.json is NOT present after initialization!"
fi