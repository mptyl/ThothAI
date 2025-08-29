#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

# Path to the secrets volume
SECRETS_DIR="/vol/secrets"
API_KEY_FILE="${SECRETS_DIR}/django_api_key"

# Wait for the API key file to be created (by backend)
echo "Waiting for API key file..."
for i in {1..30}; do
    if [ -f "${API_KEY_FILE}" ]; then
        break
    fi
    echo "Waiting for API key file... (attempt $i/30)"
    sleep 2
done

if [ -f "${API_KEY_FILE}" ]; then
    echo "Loading API key from ${API_KEY_FILE}"
    export DJANGO_API_KEY=$(cat "${API_KEY_FILE}")
    echo "API key loaded: ${DJANGO_API_KEY:0:10}..."
else
    echo "ERROR: API key file not found after 60 seconds!"
    exit 1
fi

# Run the SQL Generator
cd /app
exec python run_server.py