#!/bin/sh
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

echo "=== Starting Frontend Application ==="

# Load secrets from volume if auto-generation is enabled
if [ "$AUTO_GENERATE_SECRETS" = "true" ] && [ -d "/vol/secrets" ]; then
    echo "Loading secrets from volume..."
    
    # Load API_KEY if it exists
    if [ -f "/vol/secrets/api_key" ]; then
        export DJANGO_API_KEY=$(cat /vol/secrets/api_key)
        echo "API_KEY loaded from secrets volume"
    fi
    
    # Load NextAuth secret if it exists
    if [ -f "/vol/secrets/nextauth_secret" ]; then
        export NEXTAUTH_SECRET=$(cat /vol/secrets/nextauth_secret)
        echo "NextAuth secret loaded from secrets volume"
    fi
fi

# Start the application with the original command
exec "$@"