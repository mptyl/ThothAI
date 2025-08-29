// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';

// Register AG-Grid modules once at app initialization
ModuleRegistry.registerModules([AllCommunityModule]);

// This component doesn't render anything, it just ensures modules are registered
export function AGGridProvider() {
  return null;
}