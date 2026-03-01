// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React from 'react';
import { useWorkspace } from '@/lib/contexts/workspace-context';
import { ChevronDown } from 'lucide-react';

interface WorkspaceSelectorProps {
  compact?: boolean;
}

export function WorkspaceSelector({ compact = false }: WorkspaceSelectorProps) {
  const { workspaces, selectedWorkspace, selectWorkspace, isLoading, error } = useWorkspace();

  if (isLoading) {
    return (
      <div className={compact ? '' : 'w-full'}>
        {!compact && <label className="text-xs text-gray-400 mb-2 block">Select a Workspace</label>}
        <div className={compact
          ? 'bg-background border border-border text-muted-foreground px-2 py-1 rounded text-xs'
          : 'bg-gray-800 text-gray-400 px-3 py-2 rounded text-sm'
        }>
          Loading...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={compact ? '' : 'w-full'}>
        {!compact && <label className="text-xs text-gray-400 mb-2 block">Select a Workspace</label>}
        <div className={compact
          ? 'bg-destructive/10 text-destructive px-2 py-1 rounded text-xs'
          : 'bg-red-900/20 text-red-400 px-3 py-2 rounded text-sm'
        }>
          Error loading workspaces
        </div>
      </div>
    );
  }

  if (workspaces.length === 0) {
    return (
      <div className={compact ? '' : 'w-full'}>
        {!compact && <label className="text-xs text-gray-400 mb-2 block">Select a Workspace</label>}
        <div className={compact
          ? 'bg-background border border-border text-muted-foreground px-2 py-1 rounded text-xs'
          : 'bg-gray-800 text-gray-400 px-3 py-2 rounded text-sm'
        }>
          No workspaces
        </div>
      </div>
    );
  }

  return (
    <div className={compact ? '' : 'w-full'}>
      {!compact && (
        <label htmlFor="workspace-selector" className="text-xs text-gray-400 mb-2 block">
          Select a Workspace
        </label>
      )}
      <div className="relative">
        <select
          id={compact ? 'workspace-selector-compact' : 'workspace-selector'}
          value={selectedWorkspace?.id || ''}
          onChange={(e) => selectWorkspace(parseInt(e.target.value, 10))}
          className={compact
            ? 'bg-background border border-border text-foreground px-2 py-1 pr-6 rounded text-xs appearance-none focus:outline-none focus:ring-1 focus:ring-ring'
            : 'w-full bg-gray-800 text-white px-3 py-2 pr-8 rounded text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500'
          }
        >
          {workspaces.map((workspace) => (
            <option key={workspace.id} value={workspace.id}>
              {workspace.name}
            </option>
          ))}
        </select>
        <ChevronDown className={compact
          ? 'absolute right-1 top-1/2 transform -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none'
          : 'absolute right-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none'
        } />
      </div>
    </div>
  );
}