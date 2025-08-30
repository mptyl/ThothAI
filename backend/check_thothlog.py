#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Thoth.settings")
sys.path.insert(0, "/app")
django.setup()

from thoth_core.models import ThothLog

try:
    log = ThothLog.objects.get(id=397)
    print(f"ID: {log.id}")
    print(f"Question (first 50 chars): {log.question[:50]}...")
    print(
        f"sql_generation_failure_message present: {bool(log.sql_generation_failure_message)}"
    )
    print(
        f"sql_generation_failure_message value: [{log.sql_generation_failure_message}]"
    )
    print(
        f"Length: {len(log.sql_generation_failure_message) if log.sql_generation_failure_message else 0}"
    )
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
