// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import { apiClient } from '@/lib/api';

export interface HealthCheckResult {
  isHealthy: boolean;
  error?: string;
  serverUrl?: string;
}

export async function checkBackendHealth(): Promise<HealthCheckResult> {
  let serverUrl = '';
  try {
    serverUrl = await apiClient.getBaseUrl();
  } catch (e) {
    // If we can't get base URL, likely config failure
    return {
      isHealthy: false,
      error: 'Failed to determine backend URL configuration',
    };
  }

  try {
    const response = await fetch(`${serverUrl}/api/test_token`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Short timeout for health check
      signal: AbortSignal.timeout(5000),
    });

    // Even 401 (unauthorized) or 403 (forbidden) is fine - it means the server is running
    if (response.status === 401 || response.status === 403 || response.ok) {
      return { isHealthy: true, serverUrl };
    }
    return {
      isHealthy: false,
      error: `Server responded with status ${response.status}`,
      serverUrl,
    };

  } catch (error: any) {

    let errorMessage = 'Unable to connect to backend server';

    if (error.name === 'TimeoutError') {
      errorMessage = 'Backend server is not responding (timeout)';
    } else if (error.message?.includes('Failed to fetch') || error.message?.includes('NetworkError')) {
      errorMessage = 'Backend server is not reachable';
    } else if (error.message) {
      errorMessage = error.message;
    }

    return {
      isHealthy: false,
      error: errorMessage,
      serverUrl,
    };
  }
}