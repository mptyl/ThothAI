# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

@receiver(user_logged_in)
def set_default_workspace_on_login(sender, user, request, **kwargs):
    """
    After login, set the user's first default workspace in the session (if it exists)
    and save the authentication token for passing to the frontend.
    """
    default_ws = user.default_workspaces.first()
    if default_ws:
        request.session['selected_workspace_id'] = default_ws.pk
    
    # Get or create token for the user and save it in session
    token, created = Token.objects.get_or_create(user=user)
    request.session['auth_token'] = token.key
