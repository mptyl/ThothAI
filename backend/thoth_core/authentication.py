# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings

logger = logging.getLogger(__name__)

class ApiKeyAuthentication(BaseAuthentication):
    """
    Custom authentication class that authenticates requests based on API key.
    """
    def authenticate(self, request):
        # Force immediate logging to stderr to bypass Django logging
        import sys
        print("=" * 50, file=sys.stderr)
        print("ApiKeyAuthentication.authenticate() CALLED", file=sys.stderr)
        print(f"Request type: {type(request)}", file=sys.stderr)
        print(f"Request headers attribute exists: {hasattr(request, 'headers')}", file=sys.stderr)
        
        api_key = request.headers.get('X-API-KEY')
        print(f"API key from headers: {api_key[:10] if api_key else 'None'}...", file=sys.stderr)
        print(f"Settings API_KEY: {settings.API_KEY[:10] if settings.API_KEY else 'None'}...", file=sys.stderr)
        
        if not api_key:
            print("No API key in headers, returning None", file=sys.stderr)
            return None

        if api_key != settings.API_KEY:
            print(f"Invalid API key! Received: {api_key}", file=sys.stderr)
            print(f"Expected: {settings.API_KEY}", file=sys.stderr)
            raise AuthenticationFailed('Invalid API key')

        print("Valid API key! Returning (None, True)", file=sys.stderr)
        return (None, True)
