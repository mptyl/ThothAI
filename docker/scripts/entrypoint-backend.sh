#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

# Read Django SECRET_KEY from shared secrets volume
if [ -f "/secrets/django_secret_key" ]; then
    export SECRET_KEY=$(cat /secrets/django_secret_key)
    echo "Django SECRET_KEY loaded from secrets volume"
else
    echo "ERROR: Django SECRET_KEY not found at /secrets/django_secret_key"
    exit 1
fi

# Path to the local secrets volume for API key
SECRETS_DIR="/vol/secrets"
API_KEY_FILE="${SECRETS_DIR}/django_api_key"

# Create secrets directory if it doesn't exist
mkdir -p "${SECRETS_DIR}"

# Generate or load API key
if [ -f "${API_KEY_FILE}" ]; then
    echo "Loading existing API key from ${API_KEY_FILE}"
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

echo "API key loaded: ${DJANGO_API_KEY:0:10}..."

# Make sure Django can read the API key
export DJANGO_API_KEY="${DJANGO_API_KEY}"

# Run the original entrypoint
exec /start.sh