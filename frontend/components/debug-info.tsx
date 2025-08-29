// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

export function DebugInfo() {
  if (process.env.NODE_ENV !== 'development') {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-4 p-3 bg-yellow-100 dark:bg-yellow-900 border border-yellow-300 dark:border-yellow-700 rounded-md text-sm">
      <div className="font-semibold text-yellow-800 dark:text-yellow-200 mb-2">Debug Info</div>
      <div className="space-y-1 text-yellow-700 dark:text-yellow-300">
        <div>Django Server: {process.env.DJANGO_SERVER || 'NOT SET'}</div>
        <div>Node Env: {process.env.NODE_ENV || 'NOT SET'}</div>
        <div>Auth URL: {process.env.NEXTAUTH_URL || 'NOT SET'}</div>
      </div>
    </div>
  );
}