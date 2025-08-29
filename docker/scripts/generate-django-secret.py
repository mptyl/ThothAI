#!/usr/bin/env python3
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.

import os
import secrets
import string

SECRETS_DIR = '/secrets'
SECRET_FILE = f'{SECRETS_DIR}/django_secret_key'

def generate_secret_key(length=50):
    """Generate a Django-compatible secret key"""
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(length))

if __name__ == '__main__':
    os.makedirs(SECRETS_DIR, exist_ok=True)
    
    if not os.path.exists(SECRET_FILE):
        secret = generate_secret_key()
        with open(SECRET_FILE, 'w') as f:
            f.write(secret)
        os.chmod(SECRET_FILE, 0o640)
        print(f"Django SECRET_KEY generated and saved to {SECRET_FILE}")
    else:
        print(f"Django SECRET_KEY already exists at {SECRET_FILE}")