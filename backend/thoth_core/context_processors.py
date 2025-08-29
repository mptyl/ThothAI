# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from .models import Workspace

def workspace_context(request):
    """
    Adds workspace-related context to templates.
    """
    import os
    context = {
        'user_workspaces': None,
        'current_workspace': None, # Changed from default_workspace
        'user_is_editor': False,  # Default to False for non-authenticated users
        'frontend_url': os.environ.get('FRONTEND_URL', ''),  # Add frontend URL
        'auth_token': None,  # Token for frontend authentication
    }
    if request.user.is_authenticated:
        # Get all workspaces associated with the current user
        # This can remain if you need to list all available workspaces for selection
        user_workspaces = Workspace.objects.filter(users=request.user).order_by('name')
        context['user_workspaces'] = user_workspaces

        # Check if user belongs to the Editor group
        context['user_is_editor'] = request.user.groups.filter(name='Editor').exists()

        # The current_workspace is now set by the WorkspaceMiddleware
        # and available on the request object.
        if hasattr(request, 'current_workspace'):
            context['current_workspace'] = request.current_workspace
        # If request.current_workspace is None (e.g., no workspace selected or user not authenticated fully yet by middleware),
        # it will remain None in the context, which templates should handle.
        
        # Get auth token for frontend authentication
        # Try to get the user's API token from the database
        from rest_framework.authtoken.models import Token
        try:
            token = Token.objects.get(user=request.user)
            context['auth_token'] = token.key
        except Token.DoesNotExist:
            # If no token exists, create one
            token = Token.objects.create(user=request.user)
            context['auth_token'] = token.key
    return context
