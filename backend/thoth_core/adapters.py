# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
OIDC Social Account Adapter for ThothAI.

Normalizza i claims da Microsoft Entra ID
e gestisce il mapping di ruoli e gruppi verso Django.
"""

import logging
from typing import List, Optional

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

logger = logging.getLogger(__name__)
User = get_user_model()


class ThothSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter che normalizza i claims da Entra.
    
    Features:
    - Collegamento automatico utenti esistenti per email
    - Mapping ruoli IdP → Django Groups (configurabile via IDP_ROLE_MAPPING)
    - Sincronizzazione gruppi IdP → Django Groups
    
    TODO FUTURO: Logout federato (attualmente solo sessione locale)
    """
    
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
