#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

# Check if DJANGO_API_KEY is set from environment
if [ -z "${DJANGO_API_KEY}" ]; then
    echo "ERROR: DJANGO_API_KEY not set in environment"
    exit 1
fi

echo "API key loaded from environment: ${DJANGO_API_KEY:0:10}..."

# Get port from environment or use default
PORT=${PORT:-8001}

echo "Starting SQL Generator on port ${PORT}..."

# Run the SQL Generator
cd /app
exec python run_server.py ${PORT}