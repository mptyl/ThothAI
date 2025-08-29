#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

"""
Load API key from secrets volume for Django
"""

import os
import secrets

SECRETS_DIR = "/vol/secrets"
API_KEY_FILE = os.path.join(SECRETS_DIR, "django_api_key")

def get_or_create_api_key():
    """Get existing API key or create a new one."""
    os.makedirs(SECRETS_DIR, exist_ok=True)
    
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, 'r') as f:
            api_key = f.read().strip()
        if api_key:
            return api_key
    
    # Generate new API key
    api_key = secrets.token_urlsafe(32)
    with open(API_KEY_FILE, 'w') as f:
        f.write(api_key)
    os.chmod(API_KEY_FILE, 0o600)
    
    return api_key

if __name__ == "__main__":
    # When run as script, just print the key
    print(get_or_create_api_key())