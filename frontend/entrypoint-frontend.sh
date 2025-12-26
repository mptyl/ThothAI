#!/bin/sh
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

set -e

# Read Django API_KEY from shared secrets volume
if [ -f "/secrets/django_api_key" ]; then
    export DJANGO_API_KEY=$(cat /secrets/django_api_key)
    echo "Django API_KEY loaded from secrets volume"
    echo "API key loaded: ${DJANGO_API_KEY:0:10}..."
    
    # Also export for Next.js runtime
    export NEXT_PUBLIC_DJANGO_API_KEY="${DJANGO_API_KEY}"
else
    echo "ERROR: Django API_KEY not found at /secrets/django_api_key"
    exit 1
fi

# Create .env file for Next.js standalone to read runtime variables
# Next.js standalone mode runs server.js which reads .env from its execution directory
echo "Creating .env files for Next.js runtime..."

# Create .env in root (where server.js runs)
cat > /app/.env << EOF
RUNTIME_BACKEND_URL=${RUNTIME_BACKEND_URL}
RUNTIME_SQL_GENERATOR_URL=${RUNTIME_SQL_GENERATOR_URL}
EOF

# Also create .env.production for production mode
cat > /app/.env.production << EOF
RUNTIME_BACKEND_URL=${RUNTIME_BACKEND_URL}
RUNTIME_SQL_GENERATOR_URL=${RUNTIME_SQL_GENERATOR_URL}
EOF

echo ".env files created with RUNTIME_BACKEND_URL=${RUNTIME_BACKEND_URL}"

# Run the Next.js application with all environment variables
exec npm run start