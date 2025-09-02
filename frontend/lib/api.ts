// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { LoginRequest, LoginResponse, AuthError, WorkspaceApiResponse, WorkspaceUserListResponse } from './types';

class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    // Use direct backend URL now that CORS is configured
    this.baseURL = process.env.NEXT_PUBLIC_DJANGO_SERVER || 'http://localhost:8200';
    
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
      // Add withCredentials for CORS if needed
      withCredentials: false,
    });

    // Request interceptor to add auth token and API key
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getStoredToken();
        if (token) {
          config.headers.Authorization = `Token ${token}`;
        }
        
        // Add API key for endpoints that require it (not login)
        const apiKey = process.env.NEXT_PUBLIC_DJANGO_API_KEY || process.env.DJANGO_API_KEY;
        if (apiKey && config.url !== '/api/login') {
          config.headers['X-API-KEY'] = apiKey;
        }
        
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid, clear stored auth
          this.clearStoredAuth();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  private getStoredToken(): string | null {
    if (typeof window !== 'undefined') {
      // Check localStorage first, then sessionStorage
      return localStorage.getItem('thoth_token') || sessionStorage.getItem('thoth_token');
    }
    return null;
  }

  private clearStoredAuth(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('thoth_token');
      localStorage.removeItem('thoth_user');
      localStorage.removeItem('thoth_remember_me');
      sessionStorage.removeItem('thoth_token');
      sessionStorage.removeItem('thoth_user');
    }
  }

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    try {
      const response: AxiosResponse<LoginResponse> = await this.client.post(
        '/api/login',
        credentials
      );
      
      // Store authentication data
      if (typeof window !== 'undefined') {
        const storage = credentials.remember_me ? localStorage : sessionStorage;
        storage.setItem('thoth_token', response.data.token);
        storage.setItem('thoth_user', JSON.stringify(response.data.user));
        
        // Also store the remember preference
        localStorage.setItem('thoth_remember_me', String(credentials.remember_me));
      }
      
      return response.data;
    } catch (error: any) {
      if (error.response?.data) {
        throw error.response.data as AuthError;
      }
      throw {
        error: 'Network error',
        details: `Failed to connect to authentication server at ${this.baseURL}`
      } as AuthError;
    }
  }

  async testToken(): Promise<boolean> {
    try {
      const response = await this.client.get('/api/test_token');
      return true;
    } catch (error: any) {
      return false;
    }
  }

  async logout(): Promise<void> {
    try {
      // Note: Django backend might not have logout endpoint yet
      // but we'll clear local storage regardless
      this.clearStoredAuth();
    } catch (error) {
      // Clear local storage even if server request fails
      this.clearStoredAuth();
    }
  }

  getStoredUser() {
    if (typeof window !== 'undefined') {
      const userStr = localStorage.getItem('thoth_user') || sessionStorage.getItem('thoth_user');
      return userStr ? JSON.parse(userStr) : null;
    }
    return null;
  }

  async getWorkspaces(): Promise<WorkspaceApiResponse> {
    try {
      const response: AxiosResponse<WorkspaceApiResponse> = await this.client.get('/api/workspaces');
      return response.data;
    } catch (error: any) {
      if (error.response?.data) {
        throw error.response.data;
      }
      throw {
        error: 'Failed to fetch workspaces',
        details: 'Unable to retrieve workspace list'
      };
    }
  }

  async getWorkspacesUserList(): Promise<WorkspaceUserListResponse> {
    try {
      const response: AxiosResponse<WorkspaceUserListResponse> = await this.client.get('/api/workspaces_user_list');
      return response.data;
    } catch (error: any) {
      if (error.response?.data) {
        throw error.response.data;
      }
      throw {
        error: 'Failed to fetch workspaces user list',
        details: 'Unable to retrieve workspace user list'
      };
    }
  }

  setToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('thoth_token', token);
    }
  }

  async getCurrentUser() {
    try {
      // Try to fetch user data from the backend
      const response = await this.client.get('/api/user');
      const userData = response.data;
      
      // Store the user data
      if (typeof window !== 'undefined') {
        const storage = localStorage.getItem('thoth_remember_me') === 'true' ? localStorage : sessionStorage;
        storage.setItem('thoth_user', JSON.stringify(userData));
      }
      
      return userData;
    } catch (error) {
      // If API call fails, try to get stored user
      const storedUser = this.getStoredUser();
      if (storedUser) {
        return storedUser;
      }
      
      // No user data available
      return null;
    }
  }
}

// Export a function that creates the client to ensure environment variables are loaded
let _apiClient: ApiClient | null = null;

export const apiClient = {
  get instance(): ApiClient {
    if (!_apiClient) {
      _apiClient = new ApiClient();
    }
    return _apiClient;
  },
  
  // Proxy methods to the instance
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    return this.instance.login(credentials);
  },
  
  async testToken(): Promise<boolean> {
    return this.instance.testToken();
  },
  
  async logout(): Promise<void> {
    return this.instance.logout();
  },
  
  getStoredUser() {
    return this.instance.getStoredUser();
  },
  
  async getWorkspaces(): Promise<WorkspaceApiResponse> {
    return this.instance.getWorkspaces();
  },
  
  async getWorkspacesUserList(): Promise<WorkspaceUserListResponse> {
    return this.instance.getWorkspacesUserList();
  },

  setToken(token: string): void {
    return this.instance.setToken(token);
  },

  async getCurrentUser() {
    return this.instance.getCurrentUser();
  }
};