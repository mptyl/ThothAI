// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import { User, Workspace, SidebarFlags, SqlGenerationStrategy, WorkspaceApiResponse } from './types';
import { apiClient } from './api';

export interface PostLoginState {
  selectedWorkspace: Workspace | null;
  sqlGenerationType: SqlGenerationStrategy;
  sidebarFlags: SidebarFlags;
}

/**
 * Determines the default workspace for a user based on the default_workspace relationship
 * @param user - The logged-in user
 * @param workspaces - Available workspaces
 * @returns The default workspace or the first available workspace
 */
export function getDefaultWorkspace(user: User, workspaces: Workspace[]): Workspace | null {
  if (!workspaces.length) return null;

  // Find the default workspace - user ID should be in the workspace's default_workspace array
  for (const workspace of workspaces) {
    if (workspace.default_workspace && workspace.default_workspace.includes(user.id)) {
      return workspace;
    }
  }

  // If no default workspace found, return the first available workspace
  return workspaces[0];
}

/**
 * Converts workspace level to SQL generation strategy
 * @param level - Workspace level from backend
 * @returns Corresponding SQL generation strategy
 */
export function convertWorkspaceLevelToStrategy(level: string): SqlGenerationStrategy {
  switch (level?.toUpperCase()) {
    case 'BASIC':
      return 'Basic';
    case 'ADVANCED':
      return 'Advanced';
    case 'EXPERT':
      return 'Expert';
    default:
      return 'Basic';
  }
}

/**
 * Aggregates group profile flags using OR logic
 * @param groupProfiles - Array of group profiles from user data
 * @returns Aggregated flags with OR logic applied
 */
export function aggregateGroupFlags(groupProfiles: User['group_profiles']): Omit<SidebarFlags, 'treat_empty_result_as_error'> {
  const defaultFlags = {
    show_sql: false,
    explain_generated_query: false,
    belt_and_suspenders: false,
  };

  if (!groupProfiles || groupProfiles.length === 0) {
    // System-wide fallbacks when no group profiles exist
    return {
      show_sql: true,
      explain_generated_query: true,
      belt_and_suspenders: false,
    };
  }

  // Apply OR logic across all group profiles
  const aggregated = { ...defaultFlags };
  
  for (const profile of groupProfiles) {
    if (profile.show_sql) aggregated.show_sql = true;
    if (profile.explain_generated_query) aggregated.explain_generated_query = true;
    // Note: belt_and_suspenders is not currently part of GroupProfile, so defaults to false
  }

  return aggregated;
}

/**
 * Performs post-login initialization
 * @param user - The logged-in user
 * @returns Promise with the initialized state
 */
export async function initializePostLoginState(user: User): Promise<PostLoginState> {
  try {
    // Fetch workspaces
    const workspacesResponse: WorkspaceApiResponse = await apiClient.getWorkspaces();
    const workspaces: Workspace[] = Object.values(workspacesResponse);

    // 1. Determine default workspace
    const selectedWorkspace = getDefaultWorkspace(user, workspaces);

    // 2. Set SQL generation type from workspace level
    const sqlGenerationType = selectedWorkspace 
      ? convertWorkspaceLevelToStrategy(selectedWorkspace.level)
      : 'Basic';

    // 3. Aggregate group flags with OR logic
    const groupFlags = aggregateGroupFlags(user.group_profiles);

    // 4. Build complete sidebar flags (treat_empty_result_as_error is always false by default)
    const sidebarFlags: SidebarFlags = {
      ...groupFlags,
      treat_empty_result_as_error: false
    };

    return {
      selectedWorkspace,
      sqlGenerationType,
      sidebarFlags
    };
  } catch (error) {
    console.error('Error during post-login initialization:', error);
    
    // Return safe defaults on error
    return {
      selectedWorkspace: null,
      sqlGenerationType: 'Basic',
      sidebarFlags: {
        show_sql: true,
        explain_generated_query: true,
        treat_empty_result_as_error: false,
        belt_and_suspenders: false
      }
    };
  }
}