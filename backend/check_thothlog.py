#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
sys.path.insert(0, '/app')
django.setup()

from thoth_core.models import ThothLog

try:
    log = ThothLog.objects.get(id=397)
    print(f"ID: {log.id}")
    print(f"Question (first 50 chars): {log.question[:50]}...")
    print(f"sql_generation_failure_message present: {bool(log.sql_generation_failure_message)}")
    print(f"sql_generation_failure_message value: [{log.sql_generation_failure_message}]")
    print(f"Length: {len(log.sql_generation_failure_message) if log.sql_generation_failure_message else 0}")
    print(f"Type: {type(log.sql_generation_failure_message)}")
    
    # Check if it's stored as None, empty string, or has actual content
    if log.sql_generation_failure_message is None:
        print("Value is None")
    elif log.sql_generation_failure_message == "":
        print("Value is empty string")
    else:
        print(f"First 200 chars: {log.sql_generation_failure_message[:200]}")
except ThothLog.DoesNotExist:
    print("ThothLog with ID 397 not found")
except Exception as e:
    print(f"Error: {e}")