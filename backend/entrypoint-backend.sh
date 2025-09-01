#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

set -e

# Set Django settings module
export DJANGO_SETTINGS_MODULE=Thoth.settings

# Verify secrets volume is mounted and contains required files
if [ ! -f "/secrets/django_secret_key" ]; then
    echo "ERROR: Django SECRET_KEY not found at /secrets/django_secret_key"
    exit 1
fi

if [ ! -f "/secrets/django_api_key" ]; then
    echo "ERROR: Django API_KEY not found at /secrets/django_api_key"
    exit 1
fi

echo "Secrets volume verified - keys are available"

# Initialize shared data volume
if [ -f "/app/scripts/init-shared-data.sh" ]; then
    echo "Initializing shared data volume..."
    /app/scripts/init-shared-data.sh
fi

# Run the original entrypoint (start.sh will load the secrets)
exec /start.sh