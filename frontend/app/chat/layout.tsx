// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import React from 'react';
import { Sidebar } from '@/components/sidebar/sidebar';
import { ProtectedRoute } from '@/components/protected-route';
import { WorkspaceProvider } from '@/lib/contexts/workspace-context';
import { SidebarProvider } from '@/lib/contexts/sidebar-context';

export const dynamic = 'force-dynamic';

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const backendUrl = process.env.RUNTIME_BACKEND_URL;

  return (
    <ProtectedRoute>
      <WorkspaceProvider>
        <SidebarProvider>
          <div className="flex h-screen bg-background">
            <Sidebar backendUrl={backendUrl} />
            <div className="flex-1 flex flex-col">
              {children}
            </div>
          </div>
        </SidebarProvider>
      </WorkspaceProvider>
    </ProtectedRoute>
  );
}