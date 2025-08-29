# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestFrontendAuthentication:
    """Test frontend authentication flow."""
    
    def test_generate_frontend_token(self, api_client):
        """Test generating a frontend token for authenticated user."""
        # Create a test user
        user = User.objects.create_user(
            username='frontenduser1',
            password='testpass123',
            email='test1@example.com'
        )
        
        # Login first
        response = api_client.post(
            '/api/login',
            {'username': 'frontenduser1', 'password': 'testpass123'},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        token = response.data['token']
        
        # Set the token for authentication
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        
        # Test the generate-frontend-token endpoint
        response = api_client.get('/api/generate-frontend-token/')
        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert 'frontend_url' in response.data
        assert 'redirect_url' in response.data
        assert response.data['token'] == token
        assert '/auth/callback?token=' in response.data['redirect_url']
    
    def test_get_current_user(self, api_client):
        """Test getting current user information."""
        # Create a test user
        user = User.objects.create_user(
            username='frontenduser2',
            password='testpass123',
            email='test2@example.com',
            first_name='Test',
            last_name='User'
        )
        
        # Login first
        response = api_client.post(
            '/api/login',
            {'username': 'frontenduser2', 'password': 'testpass123'},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        token = response.data['token']
        
        # Set the token for authentication
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        
        # Test the get_current_user endpoint
        response = api_client.get('/api/user')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'frontenduser2'
        assert response.data['email'] == 'test2@example.com'
        assert response.data['first_name'] == 'Test'
        assert response.data['last_name'] == 'User'
    
    def test_frontend_token_requires_authentication(self, api_client):
        """Test that generate-frontend-token requires authentication."""
        response = api_client.get('/api/generate-frontend-token/')
        # The response can be 401 or 403 depending on configuration
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_get_current_user_requires_authentication(self, api_client):
        """Test that get_current_user requires authentication."""
        response = api_client.get('/api/user')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED