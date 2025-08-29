# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.contrib.sessions.models import Session
from thoth_core.models import Workspace

def get_current_workspace(request):
    """
    Get the current workspace from the session.
    
    Args:
        request: The HTTP request object, which should have `current_workspace`
                 attribute set by WorkspaceMiddleware.
        
    Returns:
        Workspace: The current workspace object or None if not set.
        
    Raises:
        ValueError: If no workspace is found on the request (and it's considered mandatory here).
    """
    if hasattr(request, 'current_workspace') and request.current_workspace is not None:
        return request.current_workspace
    else:
        # Depending on how strictly this function should enforce workspace presence,
        # you might raise an error or return None.
        # For now, let's raise an error if it's expected to always be there.
        raise ValueError("No current_workspace found on request. Ensure WorkspaceMiddleware is active.")
