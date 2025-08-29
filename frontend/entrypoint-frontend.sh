#!/bin/sh
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

# Also export for Next.js runtime
export NEXT_PUBLIC_DJANGO_API_KEY="${DJANGO_API_KEY}"

# Run the Next.js application
exec npm run start