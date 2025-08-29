# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

class NoCacheMiddleware(MiddlewareMixin):
    """
    Middleware per aggiungere headers anti-cache alle API responses
    """
    
    def process_response(self, request, response):
        # Applica headers anti-cache solo alle API endpoints
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['X-Data-Timestamp'] = timezone.now().isoformat()
            
            # Aggiungi header per indicare che i dati sono sempre freschi
            response['X-Cache-Status'] = 'no-cache'
        
        return response
