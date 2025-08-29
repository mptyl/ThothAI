#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.

import os
import secrets
import string

SECRETS_DIR = '/secrets'
SECRET_KEY_FILE = f'{SECRETS_DIR}/django_secret_key'
API_KEY_FILE = f'{SECRETS_DIR}/django_api_key'

def generate_secret_key(length=50):
    """Generate a Django-compatible secret key"""
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(length))

def generate_api_key(length=32):
    """Generate a secure API key using URL-safe base64 encoding"""
    return secrets.token_urlsafe(length)

if __name__ == '__main__':
    os.makedirs(SECRETS_DIR, exist_ok=True)
    
    # Generate Django SECRET_KEY
    if not os.path.exists(SECRET_KEY_FILE):
        secret = generate_secret_key()
        with open(SECRET_KEY_FILE, 'w') as f:
            f.write(secret)
        os.chmod(SECRET_KEY_FILE, 0o640)
        print(f"Django SECRET_KEY generated and saved to {SECRET_KEY_FILE}")
    else:
        print(f"Django SECRET_KEY already exists at {SECRET_KEY_FILE}")
    
    # Generate Django API_KEY
    if not os.path.exists(API_KEY_FILE):
        api_key = generate_api_key()
        with open(API_KEY_FILE, 'w') as f:
            f.write(api_key)
        os.chmod(API_KEY_FILE, 0o640)
        print(f"Django API_KEY generated and saved to {API_KEY_FILE}")
    else:
        print(f"Django API_KEY already exists at {API_KEY_FILE}")