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
