# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Custom OIDC views that use DockerAwareOpenIDConnectAdapter.

These views override allauth's default OIDC views to fix the localhost
loopback paradox when running in Docker containers.
"""

from django.http import Http404

from allauth.account.internal.decorators import login_not_required
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2CallbackView,
    OAuth2LoginView,
)

from .adapters import DockerAwareOpenIDConnectAdapter


@login_not_required
def oidc_login(request, provider_id):
    """
    Custom OIDC login view using DockerAwareOpenIDConnectAdapter.
    Replaces allauth's default openid_connect login view.
    """
    try:
        view = OAuth2LoginView.adapter_view(
            DockerAwareOpenIDConnectAdapter(request, provider_id)
        )
        return view(request)
    except SocialApp.DoesNotExist:
        raise Http404


@login_not_required
def oidc_callback(request, provider_id):
    """
    Custom OIDC callback view using DockerAwareOpenIDConnectAdapter.
    Replaces allauth's default openid_connect callback view.
    """
    try:
        view = OAuth2CallbackView.adapter_view(
            DockerAwareOpenIDConnectAdapter(request, provider_id)
        )
        return view(request)
    except SocialApp.DoesNotExist:
        raise Http404
