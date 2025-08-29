// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { checkBackendHealth, HealthCheckResult } from '@/lib/health-check';

export function BackendStatus() {
  const [healthStatus, setHealthStatus] = useState<HealthCheckResult | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  const performHealthCheck = async () => {
    setIsChecking(true);
    const result = await checkBackendHealth();
    setHealthStatus(result);
    setIsChecking(false);
  };

  useEffect(() => {
    performHealthCheck();
  }, []);

  if (isChecking && !healthStatus) {
    return (
      <div className="flex items-center justify-center p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <Loader2 className="h-4 w-4 animate-spin mr-2 text-blue-600 dark:text-blue-400" />
        <span className="text-sm text-blue-700 dark:text-blue-300">
          Checking backend server status...
        </span>
      </div>
    );
  }

  if (!healthStatus || healthStatus.isHealthy) {
    return null; // Don't show anything if healthy
  }

  return (
    <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <h3 className="font-semibold text-red-800 dark:text-red-200 mb-1">
            Backend Server Not Available
          </h3>
          <p className="text-sm text-red-700 dark:text-red-300 mb-3">
            {healthStatus.error}
          </p>
          <div className="text-xs text-red-600 dark:text-red-400 mb-3">
            Trying to connect to: <code className="bg-red-100 dark:bg-red-800/50 px-1 rounded">{healthStatus.serverUrl}</code>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button
              size="sm" 
              variant="outline"
              onClick={performHealthCheck}
              disabled={isChecking}
              className="h-8 text-xs border-red-300 dark:border-red-700"
            >
              {isChecking ? (
                <Loader2 className="h-3 w-3 animate-spin mr-1" />
              ) : (
                <RefreshCw className="h-3 w-3 mr-1" />
              )}
              Retry
            </Button>
          </div>
          <div className="mt-3 text-xs text-red-600 dark:text-red-400">
            <strong>To fix this:</strong>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>Make sure the Django backend is running</li>
              <li>Check that it&apos;s running on the correct port (8200)</li>
              <li>Verify the DJANGO_SERVER environment variable</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}