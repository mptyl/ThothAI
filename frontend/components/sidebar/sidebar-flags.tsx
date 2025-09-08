// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React from 'react';
import { useSidebar } from '@/lib/contexts/sidebar-context';

export function SidebarFlags() {
  const { flags, updateFlag } = useSidebar();

  const flagLabels: Record<keyof typeof flags, string> = {
    show_sql: 'Show SQL',
    explain_generated_query: 'Explain SQL',
    treat_empty_result_as_error: 'Treat void result as error',
    belt_and_suspenders: 'Belt and Suspenders',
  };

  return (
    <div className="space-y-3">
      {Object.entries(flags).map(([key, value]) => (
        <label
          key={key}
          className="flex items-center space-x-2 cursor-pointer text-sm"
        >
          <input
            type="checkbox"
            checked={value}
            onChange={(e) => updateFlag(key as keyof typeof flags, e.target.checked)}
            className="rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0 focus:ring-2"
          />
          <span className="text-gray-300 select-none">
            {flagLabels[key as keyof typeof flags]}
          </span>
        </label>
      ))}
    </div>
  );
}