// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React from 'react';
import { WorkspaceSelector } from './workspace-selector';
import { SidebarDivider } from './sidebar-divider';
import { ResetButton } from './reset-button';
import { SidebarFlags } from './sidebar-flags';
import { StrategySelector } from './strategy-selector';
import { SidebarLinks } from './sidebar-links';

export function Sidebar() {
  return (
    <div className="w-64 bg-gray-900 h-full border-r border-gray-700 flex flex-col">
      <div className="flex-1 overflow-y-auto p-4">
        {/* Workspace Selector */}
        <div className="mt-12">
          <WorkspaceSelector />
        </div>
        
        {/* Divider */}
        <SidebarDivider />
        
        {/* Reset Button */}
        <ResetButton />
        
        {/* Divider */}
        <SidebarDivider />
        
        {/* Sidebar Flags */}
        <SidebarFlags />
        
        {/* Divider */}
        <SidebarDivider />
        
        {/* Strategy Selector */}
        <StrategySelector />
        
        {/* Divider */}
        <SidebarDivider />
        
        {/* Navigation Links */}
        <SidebarLinks />
      </div>
    </div>
  );
}