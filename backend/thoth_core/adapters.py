# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
OIDC Social Account Adapter for ThothAI.

Normalizza i claims da Microsoft Entra ID
e gestisce il mapping di ruoli e gruppi verso Django.

Includes DockerAwareOpenIDConnectAdapter for fixing localhost URLs
in OIDC discovery when running inside Docker containers.
"""

import logging
import os
from typing import List, Optional

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.openid_connect.views import OpenIDConnectOAuth2Adapter
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

logger = logging.getLogger(__name__)
User = get_user_model()


class ThothAccountAdapter(DefaultAccountAdapter):
    """
    Custom Account Adapter following allauth best practices.
    Configured via ACCOUNT_ADAPTER setting.
    
    Overrides get_login_redirect_url to handle cross-origin redirects
    from backend to frontend after OIDC authentication.
    """
    
    def get_login_redirect_url(self, request):
        """
        Override to redirect OIDC logins to frontend with token.
        Standard allauth method for customizing post-login redirect.
        
        If the 'next' parameter points to an external URL (frontend),
        we redirect to frontend SSO callback with a token.
        """
        from rest_framework.authtoken.models import Token
        from urllib.parse import urlencode, urlparse
        
        # Get the 'next' parameter from various sources
        next_url = request.GET.get('next', '')
        frontend_url = os.environ.get('FRONTEND_URL', '')
        
        logger.info(f"[REDIRECT] get_login_redirect_url called - next='{next_url}', FRONTEND_URL='{frontend_url}'")
        
        # If user is authenticated and we have FRONTEND_URL, always redirect to frontend
        if request.user.is_authenticated and frontend_url:
            # Create or get token for the authenticated user
            token, _ = Token.objects.get_or_create(user=request.user)
            
            # Determine destination path
            if next_url:
                parsed = urlparse(next_url)
                # Extract path from absolute or relative URL
                destination = parsed.path or '/chat'
            else:
                destination = '/chat'
            
            # Build frontend SSO callback URL
            params = urlencode({'token': token.key, 'next': destination})
            callback_url = f"{frontend_url}/auth/sso-callback?{params}"
            
            logger.info(f"[REDIRECT] Redirecting to frontend: {callback_url}")
            return callback_url
        
        # Fallback to default behavior
        logger.info(f"[REDIRECT] Using default redirect (no FRONTEND_URL or not authenticated)")
        return super().get_login_redirect_url(request)


class DockerAwareOpenIDConnectAdapter(OpenIDConnectOAuth2Adapter):
    """
    Custom OAuth2 adapter that rewrites localhost URLs to host.docker.internal
    for server-side requests when running inside Docker.
    
    This fixes the token exchange when the OIDC provider (emulator) returns
    localhost URLs in its discovery document, which don't work from inside
    a Docker container.
    
    Browser redirects still use localhost (for user access), but backend
    token exchange uses host.docker.internal (for container networking).
    """
    
    def __init__(self, request, provider_id=None):
        super().__init__(request, provider_id)
        logger.info(f"DockerAwareOpenIDConnectAdapter initialized for provider: {provider_id}")
    
    def _translate_url_for_docker(self, url: str) -> str:
        """
        Translate localhost URLs to host.docker.internal when in Docker.
        """
        if not url:
            return url
        
        # Check if we're in Docker (HOST_IP env var is set in docker-compose.yml)
        if os.environ.get('HOST_IP') == 'host.docker.internal':
            # Replace localhost with host.docker.internal for server-side calls
            translated = url.replace('http://localhost:', 'http://host.docker.internal:')
            if translated != url:
                logger.info(f"URL translated for Docker: {url} -> {translated}")
            return translated
        return url
    
    @property
    def openid_config(self):
        """Override to translate the discovery URL before fetching."""
        if not hasattr(self, "_openid_config"):
            from allauth.socialaccount.adapter import get_adapter
            
            server_url = self.get_provider().server_url
            # Translate the discovery URL so we can fetch it from Docker
            translated_url = self._translate_url_for_docker(server_url)
            logger.info(f"Fetching OIDC discovery from: {translated_url}")
            
            resp = get_adapter().get_requests_session().get(translated_url)
            resp.raise_for_status()
            self._openid_config = resp.json()
            logger.info(f"OIDC discovery fetched, token_endpoint: {self._openid_config.get('token_endpoint')}")
        return self._openid_config
    
    @property
    def access_token_url(self):
        """Override to translate localhost to host.docker.internal."""
        url = self.openid_config["token_endpoint"]
        translated = self._translate_url_for_docker(url)
        logger.info(f"access_token_url property returning: {translated}")
        return translated
    
    @property
    def profile_url(self):
        """Override to translate localhost to host.docker.internal."""
        url = self.openid_config["userinfo_endpoint"]
        translated = self._translate_url_for_docker(url)
        if translated != url:
            logger.debug(f"Translated userinfo_endpoint for Docker: {url} -> {translated}")
        return translated


# Import provider class for custom registration
from allauth.socialaccount.providers.openid_connect.provider import OpenIDConnectProvider


class ThothOpenIDConnectProvider(OpenIDConnectProvider):
    """
    Custom OpenID Connect provider that uses DockerAwareOpenIDConnectAdapter.
    
    This provider must be registered in SOCIALACCOUNT_PROVIDERS to enable
    Docker-aware URL translation for token exchange.
    """
    id = "openid_connect"
    oauth2_adapter_class = DockerAwareOpenIDConnectAdapter


class ThothSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter che normalizza i claims da Entra.
    
    Features:
    - Collegamento automatico utenti esistenti per email
    - Mapping ruoli IdP → Django Groups (configurabile via IDP_ROLE_MAPPING)
    - Sincronizzazione gruppi IdP → Django Groups
    
    TODO FUTURO: Logout federato (attualmente solo sessione locale)
    """
    
    def on_authentication_error(
        self,
        request,
        provider_id,
        error=None,
        exception=None,
        extra_context=None
    ):
        """
        Hook to capture and log OIDC authentication errors.
        Called by allauth when token exchange or other auth steps fail.
        """
        import traceback
        logger.error(f"OIDC Authentication Error for provider '{provider_id}'")
        logger.error(f"Error: {error}")
        if exception:
            logger.error(f"Exception: {type(exception).__name__}: {exception}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
        if extra_context:
            logger.error(f"Extra context: {extra_context}")
        # Let parent handle the error (renders error page)
        return super().on_authentication_error(
            request, provider_id, error, exception, extra_context
        )
    
    def pre_social_login(self, request, sociallogin):
        """
        Connetti account IdP a utente locale esistente se email corrisponde.
        Questo evita duplicazione account durante la migrazione.
        """
        if sociallogin.is_existing:
            return
        
        # Cerca utente locale con stessa email
        email = self._get_email(sociallogin)
        
        if email:
            try:
                existing_user = User.objects.get(email__iexact=email)
                sociallogin.connect(request, existing_user)
                logger.info(f"Linked IdP account to existing user: {email}")
            except User.DoesNotExist:
                logger.info(f"Creating new user from IdP: {email}")
            except User.MultipleObjectsReturned:
                logger.warning(f"Multiple users with email {email}, skipping auto-link")
    
    def populate_user(self, request, sociallogin, data):
        """
        Popola dati utente da claims IdP.
        """
        user = super().populate_user(request, sociallogin, data)
        extra_data = sociallogin.account.extra_data
        
        # Nome e cognome (standard per entrambi IdP)
        user.first_name = extra_data.get('given_name', '')
        user.last_name = extra_data.get('family_name', '')
        
        # Email
        user.email = self._get_email(sociallogin) or ''
        
        # Username da UPN o email
        if not user.username:
            upn = extra_data.get('upn') or extra_data.get('preferred_username') or user.email
            user.username = upn.split('@')[0] if '@' in upn else upn
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Salva utente e sincronizza ruoli/gruppi da IdP.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Sincronizza ruoli/gruppi
        self._sync_roles(user, sociallogin)
        self._sync_groups(user, sociallogin)
        
        return user
    
    def _get_email(self, sociallogin) -> Optional[str]:
        """Estrae email dai claims."""
        extra_data = sociallogin.account.extra_data
        return (
            extra_data.get('email') or 
            extra_data.get('preferred_username') or
            extra_data.get('upn')
        )
    
    def _get_roles(self, sociallogin) -> List[str]:
        """
        Estrae i ruoli in modo normalizzato per entrambi gli IdP.
        
        - Microsoft Entra: `roles` è un array flat
        """
        extra_data = sociallogin.account.extra_data
        provider_id = sociallogin.account.provider
        
        if provider_id == "microsoft":
            return extra_data.get('roles', [])
        
        
        return []
    
    def _get_groups(self, sociallogin) -> List[str]:
        """Estrae i gruppi da claims IdP."""
        extra_data = sociallogin.account.extra_data
        return extra_data.get('groups', [])
    
    def _sync_roles(self, user, sociallogin):
        """
        Sincronizza ruoli IdP → Django Groups.
        Usa il mapping configurato in IDP_ROLE_MAPPING se presente,
        altrimenti crea gruppi Django con lo stesso nome del ruolo IdP.
        """
        from django.conf import settings
        
        roles = self._get_roles(sociallogin)
        role_mapping = getattr(settings, 'IDP_ROLE_MAPPING', {})
        
        for role_name in roles:
            # Applica mapping se configurato, altrimenti usa il nome originale
            django_group_name = role_mapping.get(role_name, role_name)
            
            group, created = Group.objects.get_or_create(name=django_group_name)
            if created:
                logger.info(f"Created Django group '{django_group_name}' from IdP role: {role_name}")
            user.groups.add(group)
        
        logger.info(f"Synced {len(roles)} roles for user {user.username}")
    
    def _sync_groups(self, user, sociallogin):
        """
        Sincronizza gruppi IdP → Django Groups.
        """
        groups = self._get_groups(sociallogin)
        
        for group_name in groups:
            # Entra ritorna nomi
            # Usiamo solo nomi leggibili (skip GUID-like strings)
            if len(group_name) == 36 and group_name.count('-') == 4:
                continue  # Skip GUID
            
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                logger.info(f"Created Django group from IdP group: {group_name}")
            user.groups.add(group)
        
        logger.info(f"Synced {len(groups)} groups for user {user.username}")
