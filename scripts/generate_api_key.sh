#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# Script to generate and persist API key for Thoth containers

set -e

# Path to the secrets volume
SECRETS_DIR="/vol/secrets"
API_KEY_FILE="${SECRETS_DIR}/django_api_key"

# Create secrets directory if it doesn't exist
mkdir -p "${SECRETS_DIR}"

# Check if API key already exists
if [ -f "${API_KEY_FILE}" ]; then
    echo "API key already exists at ${API_KEY_FILE}"
    export DJANGO_API_KEY=$(cat "${API_KEY_FILE}")
else
    echo "Generating new API key..."
    # Generate a secure random API key
    API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Save to file
    echo "${API_KEY}" > "${API_KEY_FILE}"
    chmod 600 "${API_KEY_FILE}"
    
    echo "API key generated and saved to ${API_KEY_FILE}"
    export DJANGO_API_KEY="${API_KEY}"
fi

# Export for use by the application
echo "API key loaded successfully"
echo "DJANGO_API_KEY=${DJANGO_API_KEY}"