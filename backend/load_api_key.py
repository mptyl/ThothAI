#!/usr/bin/env python3

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