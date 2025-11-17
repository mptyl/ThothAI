// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React from 'react';
import { useSidebar } from '@/lib/contexts/sidebar-context';
import { ChevronDown } from 'lucide-react';
import { SqlGenerationStrategy } from '@/lib/types';

export function StrategySelector() {
  const { strategy, updateStrategy } = useSidebar();

  const strategies: SqlGenerationStrategy[] = ['Basic', 'Advanced', 'Expert'];

  return (
    <div className="w-full">
      <label htmlFor="strategy-selector" className="text-xs text-gray-400 mb-2 block">
        First SQL Generator
      </label>
      <div className="relative">
        <select
          id="strategy-selector"
          value={strategy}
          onChange={(e) => updateStrategy(e.target.value as SqlGenerationStrategy)}
          className="w-full bg-gray-800 text-white px-3 py-2 pr-8 rounded text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {strategies.map((strat) => (
            <option key={strat} value={strat}>
              {strat}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
      </div>
    </div>
  );
}