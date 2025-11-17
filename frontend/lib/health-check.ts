// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

export interface HealthCheckResult {
  isHealthy: boolean;
  error?: string;
  serverUrl?: string;
}

export async function checkBackendHealth(): Promise<HealthCheckResult> {
  // Server-side: use DJANGO_SERVER from environment
  // Client-side: use NEXT_PUBLIC_DJANGO_SERVER
  const serverUrl = typeof window === 'undefined' 
    ? process.env.DJANGO_SERVER!
    : process.env.NEXT_PUBLIC_DJANGO_SERVER!;
  
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