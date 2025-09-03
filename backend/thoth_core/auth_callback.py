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

import logging
from django.shortcuts import redirect
from django.contrib.auth import login
from django.views import View
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


class AdminCallbackView(View):
    """Handle authentication callback from frontend with token for SSO to Django admin."""
    
    def get(self, request):
        token_key = request.GET.get('token')
        next_url = request.GET.get('next', '/admin/')  # Default to admin
        
        if token_key:
            try:
                # Get the token and associated user
                token = Token.objects.get(key=token_key)
                user = token.user
                
                # Log the user in using Django's session authentication
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Store token in session for potential future use
                request.session['auth_token'] = token.key
                request.session['frontend_authenticated'] = True
                request.session.save()
                
                logger.info(f"User {user.username} authenticated via frontend SSO token")
                
                # Check if user has admin access
                if user.is_staff or user.is_superuser:
                    # Redirect to admin or requested URL
                    return redirect(next_url)
                else:
                    # User doesn't have admin access, redirect to home
                    logger.warning(f"User {user.username} attempted to access admin without permissions")
                    return redirect('/')
                    
            except Token.DoesNotExist:
                logger.warning(f"Invalid token attempted for SSO: {token_key[:8]}...")
                # Invalid token, redirect to login
                return redirect('/admin/login/?next=' + next_url)
        
        # No token provided, redirect to login
        logger.info("SSO attempted without token")
        return redirect('/admin/login/?next=' + next_url)