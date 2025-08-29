# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import logging
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.conf import settings

logger = logging.getLogger(__name__)

class HasValidApiKey(BasePermission):
    """
    Custom permission to check if the request has a valid API key.
    This permission is satisfied if:
    - The request was authenticated via ApiKeyAuthentication (request.auth is True), OR
    - The request contains a valid API key header
    """
    def has_permission(self, request, view):
        # If authenticated via API key (ApiKeyAuthentication sets auth=True, user=None)
        if request.auth is True and request.user is None:
            logger.debug("HasValidApiKey: Request authenticated via API key")
            return True
        
        # Otherwise check for API key in headers
        api_key = request.headers.get('X-API-KEY')
        if not api_key:
            logger.debug("HasValidApiKey: No API key in headers")
            return False
        
        result = api_key == settings.API_KEY
        logger.debug(f"HasValidApiKey: API key validation result: {result}")
        return result


class IsAuthenticatedOrHasApiKey(BasePermission):
    """
    Allows access if the request is authenticated OR has a valid API key.
    This combines IsAuthenticated and HasValidApiKey permissions.
    """
    def has_permission(self, request, view):
        # Check IsAuthenticated permission
        is_auth_perm = IsAuthenticated()
        if is_auth_perm.has_permission(request, view):
            logger.debug("IsAuthenticatedOrHasApiKey: User is authenticated")
            return True
        
        # Check HasValidApiKey permission
        api_key_perm = HasValidApiKey()
        if api_key_perm.has_permission(request, view):
            logger.debug("IsAuthenticatedOrHasApiKey: Has valid API key")
            return True
        
        logger.debug("IsAuthenticatedOrHasApiKey: No valid authentication")
        return False