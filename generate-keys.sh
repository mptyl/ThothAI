#!/bin/bash
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

# Script to generate secure keys for ThothAI configuration

set -e

echo "=== ThothAI Key Generator ==="

# Function to generate Django SECRET_KEY
generate_django_secret() {
    python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null
}

# Function to generate API_KEY
generate_api_key() {
    python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('='))" 2>/dev/null
}

echo "Generating new secure keys..."
echo ""

SK=$(generate_django_secret)
AK=$(generate_api_key)

echo "----------------------------------------------------------"
echo "SECRET_KEY:"
echo "$SK"
echo "----------------------------------------------------------"
echo "DJANGO_API_KEY:"
echo "$AK"
echo "----------------------------------------------------------"
echo ""
echo "Copy these values into your .env.local or .env.swarm files."
echo "Keep these keys secret and do not share them."
