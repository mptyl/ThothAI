// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import { useAuth } from '@/lib/auth-context';

export default function TestAuthPage() {
  const auth = useAuth();

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="bg-card border rounded-lg p-6 max-w-md w-full">
        <h1 className="text-xl font-bold mb-4">Auth State Debug</h1>
        
        <div className="space-y-2 text-sm">
          <div><strong>isLoading:</strong> {auth.isLoading ? 'true' : 'false'}</div>
          <div><strong>isAuthenticated:</strong> {auth.isAuthenticated ? 'true' : 'false'}</div>
          <div><strong>error:</strong> {auth.error || 'null'}</div>
          <div><strong>user:</strong> {auth.user ? auth.user.username : 'null'}</div>
          <div><strong>token:</strong> {auth.token ? 'present' : 'null'}</div>
        </div>

        <div className="mt-4 p-3 bg-muted rounded text-xs">
          <strong>Environment:</strong><br/>
          DJANGO_SERVER: {process.env.DJANGO_SERVER || 'NOT SET'}
        </div>
      </div>
    </div>
  );
}