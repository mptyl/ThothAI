# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

from django.shortcuts import redirect
from django.contrib.auth import login
from django.views import View
from rest_framework.authtoken.models import Token


class AdminCallbackView(View):
    """Handle authentication callback from frontend with token."""
    
    def get(self, request):
        token_key = request.GET.get('token')
        
        if token_key:
            try:
                # Get the token and associated user
                token = Token.objects.get(key=token_key)
                user = token.user
                
                # Log the user in
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Redirect to backend home page
                return redirect('/')
            except Token.DoesNotExist:
                # Invalid token, redirect to login
                return redirect('/accounts/login/')
        
        # No token provided, redirect to login
        return redirect('/accounts/login/')