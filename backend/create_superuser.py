#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thoth_ai_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model

def create_superuser():
    User = get_user_model()
    
    # Check if admin user already exists
    if User.objects.filter(username='admin').exists():
        print("Admin user already exists")
        return
    
    # Create superuser
    user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )
    
    print(f"Superuser created successfully:")
    print(f"  Username: admin")
    print(f"  Password: admin123")
    print(f"  Email: admin@example.com")
    print("\nPlease change the password after first login!")

if __name__ == "__main__":
    create_superuser()