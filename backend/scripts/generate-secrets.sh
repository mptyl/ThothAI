#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# Script to generate secrets for Docker deployment

set -e

SECRETS_DIR="/vol/secrets"
LOCK_FILE="$SECRETS_DIR/.initialized"

# Create secrets directory if it doesn't exist
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Function to generate Django SECRET_KEY
generate_django_secret() {
    python3 -c "
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
"
}

# Function to generate API_KEY
generate_api_key() {
    python3 -c "
import secrets
import base64
# Generate a 32-byte random key and encode it to base64
key = secrets.token_bytes(32)
print(base64.urlsafe_b64encode(key).decode('utf-8').rstrip('='))
"
}

# Function to generate NextAuth secret
generate_nextauth_secret() {
    python3 -c "
import secrets
print(secrets.token_hex(32))
"
}

# Check if this is the first initialization
if [ ! -f "$LOCK_FILE" ]; then
    echo "First time initialization - generating all secrets..."
    
    # Generate Django SECRET_KEY
    if [ ! -f "$SECRETS_DIR/django_secret_key" ]; then
        echo "Generating Django SECRET_KEY..."
        generate_django_secret > "$SECRETS_DIR/django_secret_key"
        chmod 600 "$SECRETS_DIR/django_secret_key"
        echo "Django SECRET_KEY generated successfully"
    fi
    
    # Generate API_KEY for internal communication
    if [ ! -f "$SECRETS_DIR/api_key" ]; then
        echo "Generating API_KEY..."
        generate_api_key > "$SECRETS_DIR/api_key"
        chmod 600 "$SECRETS_DIR/api_key"
        echo "API_KEY generated successfully"
    fi
    
    # Generate NextAuth secret
    if [ ! -f "$SECRETS_DIR/nextauth_secret" ]; then
        echo "Generating NextAuth secret..."
        generate_nextauth_secret > "$SECRETS_DIR/nextauth_secret"
        chmod 600 "$SECRETS_DIR/nextauth_secret"
        echo "NextAuth secret generated successfully"
    fi
    
    # Create lock file to indicate initialization is complete
    touch "$LOCK_FILE"
    echo "Secrets initialization complete"
else
    echo "Secrets already initialized - loading existing values"
fi

# Export secrets as environment variables for use by the application
if [ -f "$SECRETS_DIR/django_secret_key" ]; then
    export SECRET_KEY=$(cat "$SECRETS_DIR/django_secret_key")
fi

if [ -f "$SECRETS_DIR/api_key" ]; then
    export DJANGO_API_KEY=$(cat "$SECRETS_DIR/api_key")
fi

if [ -f "$SECRETS_DIR/nextauth_secret" ]; then
    export NEXTAUTH_SECRET=$(cat "$SECRETS_DIR/nextauth_secret")
fi

echo "Secrets loaded into environment"