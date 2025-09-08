// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

/**
 * SQL Generator API Client
 * 
 * This module provides functions to interact with the SQL Generator FastAPI service.
 */

import axios, { AxiosInstance } from 'axios';
import { SidebarFlags, SqlGenerationStrategy } from './types';
import { abortManager } from './services/abort-manager';

// Types for API requests and responses
export interface GenerateSQLRequest {
  question: string;
  workspace_id: number;
  functionality_level: SqlGenerationStrategy;
  flags: SidebarFlags;
}

export interface GenerateSQLResponse {
  message: string;
  status: string;
}

export interface HealthResponse {
  status: string;
  message: string;
}

/**
 * SQL Generator API Client
 */
class SqlGeneratorApiClient {
  private client: AxiosInstance;
  private baseURL: string;
  private currentRequestId: string | null = null;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_SQL_GENERATOR_URL || 'http://localhost:8001';
    
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 60000, // Increased to 60 seconds for complex AI processing
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        // Debug logging in development only
        if (process.env.NODE_ENV === 'development') {
          console.log(`SQL Generator API: ${config.method?.toUpperCase()} ${config.url}`);
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response) {
          console.error('SQL Generator API Error:', error.response.data);
          throw new Error(error.response.data.detail || 'API request failed');
        } else if (error.request) {
          console.error('SQL Generator API Network Error:', error.message);
          throw new Error('Network error - SQL Generator service may be unavailable');
        } else {
          console.error('SQL Generator API Error:', error.message);
          throw new Error(error.message);
        }
      }
    );
  }

  /**
   * Check the health status of the SQL Generator service
   */
  async healthCheck(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }

  /**
   * Cancel the current request if one is active
   */
  cancelCurrentRequest(): boolean {
    if (this.currentRequestId) {
      const cancelled = abortManager.abort(this.currentRequestId, 'User cancelled operation');
      this.currentRequestId = null;
      // Debug logging in development only
      if (process.env.NODE_ENV === 'development') {
        console.log('[SqlGeneratorApiClient] Request cancelled:', cancelled);
      }
      return cancelled;
    }
    return false;
  }

  /**
   * Generate SQL from natural language question (streaming)
   */
  async generateSQLStream(request: GenerateSQLRequest, username?: string, onMessage?: (message: string) => void): Promise<void> {
    // Cancel any existing request
    this.cancelCurrentRequest();
    
    // Create a unique request ID
    const requestId = `sql-generation-${Date.now()}`;
    this.currentRequestId = requestId;
    
    // Use Next.js same-origin proxy to bypass CORS and simplify local/dev setup
    const url = `/api/sql-proxy`;
    
    // Get AbortController from centralized manager
    const controller = abortManager.createController(requestId);
    const timeoutId = setTimeout(() => {
      abortManager.abort(requestId, 'Request timeout');
    }, 120000); // 2 minutes timeout
    
    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        'Accept': 'text/plain',
      };
      
      // Include username header if provided
      if (username) {
        headers['X-Username'] = username;
      }
      
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const body = await response.text().catch(() => '');
        
        // Handle specific error codes
        if (response.status === 504) {
          throw new Error('Request timeout - SQL generation took too long. Please try again with a simpler query.');
        }
        if (response.status === 502) {
          throw new Error('SQL Generator service is unavailable. Please ensure the backend is running.');
        }
        
        throw new Error(`HTTP ${response.status} ${response.statusText} - ${body?.slice(0, 500)}`);
      }

      if (!response.body) {
        throw new Error('Response body is not readable');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          if (chunk && onMessage) {
            onMessage(chunk);
          }
        }
        
        // Clean up on successful completion
        clearTimeout(timeoutId);
        abortManager.cleanup(requestId);
        this.currentRequestId = null;
        
      } catch (readError) {
        // Handle read errors gracefully
        if (readError instanceof Error && readError.name === 'AbortError') {
          throw new Error('Request was cancelled');
        }
        // If it's a different error during reading, log it but don't throw
        console.warn('Stream reading warning:', readError);
      } finally {
        try {
          reader.releaseLock();
        } catch {
          // Reader already released, ignore
        }
      }
    } catch (error) {
      clearTimeout(timeoutId);
      
      // Clean up the abort controller
      abortManager.cleanup(requestId);
      this.currentRequestId = null;
      
      // Handle different error types
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          // Check if it was user cancellation or timeout
          const reason = abortManager.getController(requestId)?.signal.reason;
          if (reason === 'User cancelled operation') {
            throw new Error('Operation cancelled by user');
          }
          throw new Error('Request timeout - SQL generation took too long. Please try again.');
        }
        
        console.error('Streaming error:', error);
        
        // If the error message already contains useful info, pass it through
        if (error.message.includes('SQL Generator') || 
            error.message.includes('timeout') || 
            error.message.includes('unavailable')) {
          throw error;
        }
        
        // Otherwise, wrap it with context
        throw new Error(`Failed to contact SQL Generator. Reason: ${error.message}`);
      }
      
      throw new Error('Failed to contact SQL Generator service');
    }
  }

  /**
   * Generate SQL from natural language question (non-streaming fallback)
   */
  async generateSQL(request: GenerateSQLRequest): Promise<GenerateSQLResponse> {
    const response = await this.client.post<GenerateSQLResponse>('/generate-sql', request);
    return response.data;
  }

  /**
   * Get the base URL of the SQL Generator service
   */
  getBaseURL(): string {
    return this.baseURL;
  }
}

// Export a singleton instance
export const sqlGeneratorApi = new SqlGeneratorApiClient();