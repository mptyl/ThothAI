// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { WorkspaceUserItem, WorkspaceUserListResponse, Workspace, WorkspaceApiResponse } from '@/lib/types';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { getDefaultWorkspace } from '@/lib/post-login-init';

interface WorkspaceContextType {
  workspaces: WorkspaceUserItem[];
  selectedWorkspace: WorkspaceUserItem | null;
  fullWorkspaceData: Workspace | null; // Full workspace data for SQL generation level
  isLoading: boolean;
  error: string | null;
  isPostLoginInitialized: boolean;
  selectWorkspace: (workspaceId: number) => void;
  refreshWorkspaces: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [workspaces, setWorkspaces] = useState<WorkspaceUserItem[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<WorkspaceUserItem | null>(null);
  const [fullWorkspaceData, setFullWorkspaceData] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPostLoginInitialized, setIsPostLoginInitialized] = useState(false);
  const { user, isAuthenticated } = useAuth();

  // Load workspaces and perform post-login initialization
  const loadWorkspaces = useCallback(async () => {
    if (!isAuthenticated || !user) {
      setIsLoading(false);
      setIsPostLoginInitialized(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Only do post-login initialization once per login session
      if (!isPostLoginInitialized) {
        // Fetch full workspace data for default workspace selection and SQL generation level
        const fullWorkspaces: Workspace[] = await apiClient.getWorkspaces();

        // Get default workspace using the same logic as Streamlit
        const defaultWorkspace = getDefaultWorkspace(user, fullWorkspaces);

        if (defaultWorkspace) {
          setFullWorkspaceData(defaultWorkspace);

          // Convert to simplified workspace format for the selector
          const selectedWorkspaceSimple: WorkspaceUserItem = {
            id: defaultWorkspace.id,
            name: defaultWorkspace.name,
          };
          setSelectedWorkspace(selectedWorkspaceSimple);
        }

        // Also fetch workspace user list for the selector
        const workspaceArray = await apiClient.getWorkspacesUserList();
        setWorkspaces(workspaceArray);

        setIsPostLoginInitialized(true);
      } else {
        // Regular workspace loading (not post-login initialization)
        const workspaceArray = await apiClient.getWorkspacesUserList();
        setWorkspaces(workspaceArray);

        // Restore workspace selection from local storage if not in post-login mode
        if (workspaceArray.length > 0 && !selectedWorkspace) {
          const savedWorkspaceId = localStorage.getItem('thoth_selected_workspace_id');
          let workspaceToSelect: WorkspaceUserItem | null = null;

          if (savedWorkspaceId) {
            const workspaceId = parseInt(savedWorkspaceId, 10);
            workspaceToSelect = workspaceArray.find(w => w.id === workspaceId) || null;
          }

          if (!workspaceToSelect) {
            workspaceToSelect = workspaceArray[0];
          }

          setSelectedWorkspace(workspaceToSelect);
          localStorage.setItem('thoth_selected_workspace_id', workspaceToSelect.id.toString());
        }
      }
    } catch (err: any) {
      console.error('Failed to load workspaces:', err);
      setError(err.error || 'Failed to load workspaces');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, user, isPostLoginInitialized, selectedWorkspace]);

  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces]);

  const selectWorkspace = useCallback(async (workspaceId: number) => {
    const workspace = workspaces.find(w => w.id === workspaceId);
    if (workspace) {
      setSelectedWorkspace(workspace);
      localStorage.setItem('thoth_selected_workspace_id', workspace.id.toString());

      // Also fetch the full workspace data for this workspace
      try {
        const fullWorkspaces: Workspace[] = await apiClient.getWorkspaces();
        const fullWorkspace = fullWorkspaces.find(w => w.id === workspaceId);
        if (fullWorkspace) {
          setFullWorkspaceData(fullWorkspace);
        }
      } catch (err: any) {
        console.error('Failed to load full workspace data:', err);
      }
    }
  }, [workspaces]);

  const refreshWorkspaces = useCallback(async () => {
    await loadWorkspaces();
  }, [loadWorkspaces]);

  // Reset initialization state when user logs out
  useEffect(() => {
    if (!isAuthenticated || !user) {
      setIsPostLoginInitialized(false);
      setSelectedWorkspace(null);
      setFullWorkspaceData(null);
      setWorkspaces([]);
      setError(null);
    }
  }, [isAuthenticated, user]);

  const value: WorkspaceContextType = {
    workspaces,
    selectedWorkspace,
    fullWorkspaceData,
    isLoading,
    error,
    isPostLoginInitialized,
    selectWorkspace,
    refreshWorkspaces,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}
