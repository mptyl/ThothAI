import os
import sys
import django
from django.conf import settings

# Determine the correct settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')
django.setup()

import json

print("\n--- SOCIALACCOUNT_PROVIDERS ---")
providers = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {})
print(json.dumps(providers, indent=2, default=str))

print("\n--- INSTALLED_APPS ---")
apps = getattr(settings, 'INSTALLED_APPS', [])
print([app for app in apps if 'allauth' in app])

print("\n--- AUTH_MODE ---")
print(getattr(settings, 'AUTH_MODE', 'NOT_SET'))

print("\n--- ENTRA_ENABLED (ENV) ---")
print(os.environ.get('ENTRA_ENABLED'))
