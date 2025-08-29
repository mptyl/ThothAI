# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from functools import wraps
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

def require_editor_group(view_func):
    """
    Decorator that requires the user to be in the 'Editor' group to access the view.
    If the user is not in the Editor group, raises PermissionDenied.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # This should be handled by @login_required, but just in case
            return redirect('login')
        
        if not request.user.groups.filter(name='Editor').exists():
            messages.error(request, "Only users in the Editor group can perform this action.")
            raise PermissionDenied("Only users in the Editor group can perform this action.")
        
        return view_func(request, *args, **kwargs)
    return wrapper

def require_editor_group_with_redirect(redirect_view_name):
    """
    Decorator that requires the user to be in the 'Editor' group.
    If not, redirects to the specified view with an error message.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            if not request.user.groups.filter(name='Editor').exists():
                messages.error(request, "Only users in the Editor group can perform this action.")
                return redirect(redirect_view_name)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
