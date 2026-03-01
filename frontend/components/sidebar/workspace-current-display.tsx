// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React from 'react';
import { useWorkspace } from '@/lib/contexts/workspace-context';

export function WorkspaceCurrentDisplay() {
  const { selectedWorkspace } = useWorkspace();

  if (!selectedWorkspace) return null;

  return (
    <div className="px-1 py-2">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Workspace</p>
      <p className="text-sm text-gray-300 truncate">{selectedWorkspace.name}</p>
    </div>
  );
}
