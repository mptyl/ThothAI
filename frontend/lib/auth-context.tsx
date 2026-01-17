// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User, AuthState, LoginRequest } from './types';
import { apiClient } from './api';

interface AuthConfig {
  mode: 'native' | 'single_idp' | 'multi';
  providers: AuthProvider[];
  primary_provider: string | null;
  registration_enabled: boolean;
  password_reset_enabled: boolean;
}

export interface AuthProvider {
  id: string;
  name: string;
  type: 'credentials' | 'oidc';
  login_url?: string;
}

export type { AuthConfig };

interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  loginWithToken: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

/**
 * Redirect to OIDC provider login.
 * Called when user clicks on IdP button (e.g., "Microsoft Entra ID").
 */
export function loginWithOIDC(providerId: string, redirectTo?: string) {
  const backendUrl = process.env.NEXT_PUBLIC_DJANGO_SERVER || 'http://localhost:8040';
  const next = redirectTo || window.location.pathname;

  // Redirect al backend Django che gestisce OIDC
  window.location.href = `${backendUrl}/accounts/openid_connect/login/?process=login&provider_id=${providerId}&next=${encodeURIComponent(next)}`;
}

/**
 * Fetch dynamic auth configuration from backend.
 * Determines which providers are available and auth mode.
 */
export async function fetchAuthConfig(): Promise<AuthConfig> {
  const backendUrl = process.env.NEXT_PUBLIC_DJANGO_SERVER || 'http://localhost:8040';
  const response = await fetch(`${backendUrl}/api/auth-config`);
  if (!response.ok) {
    throw new Error('Failed to fetch auth config');
  }
  return response.json();
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  // Check for existing authentication on mount and when storage changes
  useEffect(() => {
    const checkExistingAuth = async () => {
      try {
        const storedUser = apiClient.getStoredUser();
        const storedToken = typeof window !== 'undefined'
          ? (localStorage.getItem('thoth_token') || sessionStorage.getItem('thoth_token'))
          : null;

        if (storedUser && storedToken) {
          try {
            // Verify token is still valid
            const isValid = await apiClient.testToken();

            if (isValid) {
              setState({
                user: storedUser,
                token: storedToken,
                isAuthenticated: true,
                isLoading: false,
                error: null,
              });
              return;
            }
          } catch (networkError) {
            // If network error, assume token is valid and let user continue
            // The error will surface when they try to make API calls
            // Debug logging in development only
            if (process.env.NODE_ENV === 'development') {
              console.log('Network error during token validation, assuming token valid');
            }
            setState({
              user: storedUser,
              token: storedToken,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });
            return;
          }
        }
      } catch (error) {
        console.error('Error checking existing auth:', error);
      }

      // No valid auth found
      // Debug logging in development only
      if (process.env.NODE_ENV === 'development') {
        console.log('No valid auth found, setting unauthenticated');
      }
      setState(prev => ({
        ...prev,
        isLoading: false,
      }));
    };

    checkExistingAuth();

    // Listen for storage changes (for cross-tab synchronization)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'thoth_token' || e.key === 'thoth_user') {
        checkExistingAuth();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const login = async (credentials: LoginRequest) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await apiClient.login(credentials);

      setState({
        user: response.user,
        token: response.token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error.error || 'Login failed',
      }));
      throw error;
    }
  };

  const loginWithToken = async (token: string) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // Store the token first
      if (typeof window !== 'undefined') {
        localStorage.setItem('thoth_token', token);
      }

      // Get user data using the token
      const userData = await apiClient.getCurrentUser();

      if (userData) {
        // Store user data
        if (typeof window !== 'undefined') {
          localStorage.setItem('thoth_user', JSON.stringify(userData));
        }

        setState({
          user: userData,
          token: token,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      } else {
        throw new Error('Failed to get user data');
      }
    } catch (error: any) {
      // Clear invalid token
      if (typeof window !== 'undefined') {
        localStorage.removeItem('thoth_token');
      }

      setState(prev => ({
        ...prev,
        isLoading: false,
        isAuthenticated: false,
        error: 'Failed to authenticate with token',
      }));
      throw error;
    }
  };

  const logout = async () => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      await apiClient.logout();
    } finally {
      setState({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
  };

  const clearError = () => {
    setState(prev => ({ ...prev, error: null }));
  };

  const contextValue: AuthContextType = {
    ...state,
    login,
    loginWithToken,
    logout,
    clearError,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}