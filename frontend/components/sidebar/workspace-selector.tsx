// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React from 'react';
import { useWorkspace } from '@/lib/contexts/workspace-context';
import { ChevronDown } from 'lucide-react';

export function WorkspaceSelector() {
  const { workspaces, selectedWorkspace, selectWorkspace, isLoading, error } = useWorkspace();

  if (isLoading) {
    return (
      <div className="w-full">
        <label className="text-xs text-gray-400 mb-2 block">Select a Workspace</label>
        <div className="bg-gray-800 text-gray-400 px-3 py-2 rounded text-sm">
          Loading workspaces...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full">
        <label className="text-xs text-gray-400 mb-2 block">Select a Workspace</label>
        <div className="bg-red-900/20 text-red-400 px-3 py-2 rounded text-sm">
          Error loading workspaces
        </div>
      </div>
    );
  }

  if (workspaces.length === 0) {
    return (
      <div className="w-full">
        <label className="text-xs text-gray-400 mb-2 block">Select a Workspace</label>
        <div className="bg-gray-800 text-gray-400 px-3 py-2 rounded text-sm">
          No workspaces available
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <label htmlFor="workspace-selector" className="text-xs text-gray-400 mb-2 block">
        Select a Workspace
      </label>
      <div className="relative">
        <select
          id="workspace-selector"
          value={selectedWorkspace?.id || ''}
          onChange={(e) => selectWorkspace(parseInt(e.target.value, 10))}
          className="w-full bg-gray-800 text-white px-3 py-2 pr-8 rounded text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {workspaces.map((workspace) => (
            <option key={workspace.id} value={workspace.id}>
              {workspace.name}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
      </div>
    </div>
  );
}