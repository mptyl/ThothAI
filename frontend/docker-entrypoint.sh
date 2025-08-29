#!/bin/sh
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

echo "=== Starting Frontend Application ==="

# Check if required environment variables are set
if [ -z "${DJANGO_API_KEY}" ]; then
    echo "ERROR: DJANGO_API_KEY not set in environment"
    exit 1
fi

if [ -z "${NEXTAUTH_SECRET}" ]; then
    echo "ERROR: NEXTAUTH_SECRET not set in environment"
    exit 1
fi

echo "Environment variables loaded successfully"

# Start the application with the original command
exec "$@"