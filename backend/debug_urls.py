import os
import sys
import django
from django.conf import settings
from django.urls import get_resolver

# Determine the correct settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Thoth.settings')

# Setup Django
django.setup()

def list_urls(lis, acc=None):
    if acc is None:
        acc = []
    if not lis:
        return
    l = lis[0]
    if hasattr(l, 'url_patterns'):
        list_urls(l.url_patterns, acc + [str(l.pattern)])
    elif hasattr(l, 'pattern'):
        print(''.join(acc) + str(l.pattern))
    
    if len(lis) > 1:
        list_urls(lis[1:], acc)

try:
    resolver = get_resolver()
    list_urls(resolver.url_patterns)
except Exception as e:
    print(f"Error listing URLs: {e}")
