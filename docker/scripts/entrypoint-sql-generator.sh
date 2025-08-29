#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

# Read Django API_KEY from shared secrets volume
if [ -f "/secrets/django_api_key" ]; then
    export DJANGO_API_KEY=$(cat /secrets/django_api_key)
    echo "Django API_KEY loaded from secrets volume"
    echo "API key loaded: ${DJANGO_API_KEY:0:10}..."
else
    echo "ERROR: Django API_KEY not found at /secrets/django_api_key"
    exit 1
fi

# Run the SQL Generator
cd /app
exec python run_server.py