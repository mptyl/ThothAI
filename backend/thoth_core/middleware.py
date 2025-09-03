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
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

# Assuming your Workspace model is in thoth_core.models
# Adjust the import if your Workspace model is located elsewhere
try:
    from thoth_core.models import Workspace
except ImportError:
    # Fallback or raise a more specific error if Workspace model is critical
    # and its location is uncertain. For now, we'll allow it to fail at runtime
    # if not found, prompting for the correct location.
    Workspace = None

logger = logging.getLogger(__name__)


class WorkspaceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """
        Adds the current_workspace to the request object.
        The workspace_id is expected to be stored in the session
        under the key 'selected_workspace_id'.
        If not in session, it tries the user's model default.
        """
        request.current_workspace = None
        if (
            request.user.is_authenticated and Workspace
        ):  # Ensure Workspace model is loaded
            selected_workspace_id = request.session.get("selected_workspace_id")

            if selected_workspace_id:
                try:
                    # Ensure the workspace from session belongs to the user
                    workspace_from_session = Workspace.objects.get(
                        id=selected_workspace_id, users=request.user
                    )
                    request.current_workspace = workspace_from_session
                except Workspace.DoesNotExist:
                    logger.warning(
                        f"User {request.user.username} - Invalid workspace_id {selected_workspace_id} in session or user lacks access. Clearing from session."
                    )
                    request.session.pop("selected_workspace_id", None)
                    # Fall through to set model default if any

            # If no valid workspace from session, try to set user's model default
            if not request.current_workspace:
                # default_workspaces is the related_name from User to Workspace's default_workspace field
                default_ws_from_model = request.user.default_workspaces.first()
                if default_ws_from_model:
                    # Verify this model default is also in the user's general accessible workspaces
                    if request.user.workspaces.filter(
                        pk=default_ws_from_model.pk
                    ).exists():
                        request.current_workspace = default_ws_from_model
                        # Optionally, you might want to set this in the session if you want it to "stick"
                        # request.session['selected_workspace_id'] = default_ws_from_model.id
                    else:
                        logger.warning(
                            f"User {request.user.username}'s model default workspace (ID: {default_ws_from_model.pk}, Name: {default_ws_from_model.name}) is not in their accessible workspaces (user.workspaces)."
                        )
                # else:
                # Optional: If still no current_workspace (no session, no model default),
                # you could pick the first available workspace for the user.
                # first_available = request.user.workspaces.order_by('name').first()
                # if first_available:
                #     request.current_workspace = first_available
                #     logger.debug(f"User {request.user.username} - Workspace from first available: {first_available.name}")
                # request.session['selected_workspace_id'] = first_available.id

            if request.current_workspace:
                logger.info(
                    f"User {request.user.username} - Current workspace set to: {request.current_workspace.name} (ID: {request.current_workspace.pk})"
                )
            else:
                logger.info(
                    f"User {request.user.username} - No current workspace could be determined."
                )

        return None  # Continue processing the request


class TokenAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to automatically authenticate users based on token in session or header.
    This enables seamless SSO between frontend and Django admin.
    """
    
    def process_request(self, request):
        # Skip if user is already authenticated
        if not request.user.is_authenticated:
            token_key = None
            
            # Try to get token from session first (set by SSO callback)
            if hasattr(request, 'session') and 'auth_token' in request.session:
                token_key = request.session.get('auth_token')
                
            # Try to get token from Authorization header
            if not token_key:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header.startswith('Token '):
                    token_key = auth_header.split(' ')[1]
            
            # Try to get token from X-Auth-Token header (alternative)
            if not token_key:
                token_key = request.META.get('HTTP_X_AUTH_TOKEN')
            
            # If we have a token, try to authenticate
            if token_key:
                try:
                    token = Token.objects.select_related('user').get(key=token_key)
                    user = token.user
                    
                    # Only auto-login if user is active
                    if user.is_active:
                        # Set the user on the request
                        request.user = user
                        request._cached_user = user
                        
                        # If this is an admin URL and user has permissions, ensure they're logged in
                        if request.path.startswith('/admin/') and (user.is_staff or user.is_superuser):
                            # Use login to create session if not exists
                            if not request.session.get('_auth_user_id'):
                                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                                logger.debug(f"Auto-logged in user {user.username} for admin access")
                        
                except Token.DoesNotExist:
                    logger.debug(f"Invalid token in middleware: {token_key[:8] if token_key else 'None'}...")
                except Exception as e:
                    logger.error(f"Error in token authentication middleware: {e}")
        
        return None  # Continue processing


class SessionRefreshMiddleware(MiddlewareMixin):
    """
    Middleware to keep session alive when user is active.
    """
    
    def process_request(self, request):
        # Refresh session expiry on each request if user is authenticated
        if hasattr(request, 'session') and request.user.is_authenticated:
            if not request.session.get_expire_at_browser_close():
                # Keep session alive for 2 hours of inactivity
                request.session.set_expiry(7200)
        
        return None  # Continue processing
