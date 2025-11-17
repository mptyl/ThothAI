// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { SidebarFlags, SqlGenerationStrategy } from '@/lib/types';
import { useAuth } from '@/lib/auth-context';
import { useWorkspace } from './workspace-context';
import { aggregateGroupFlags, convertWorkspaceLevelToStrategy } from '@/lib/post-login-init';
import { sqlGeneratorApi } from '@/lib/sql-generator-api';

interface SidebarContextType {
  flags: SidebarFlags;
  strategy: SqlGenerationStrategy;
  isInitialized: boolean;
  isOperationInProgress: boolean;
  currentOperationId: string | null;
  updateFlag: (flag: keyof SidebarFlags, value: boolean) => void;
  updateStrategy: (strategy: SqlGenerationStrategy) => void;
  resetToDefaults: () => void;
  setOperationInProgress: (inProgress: boolean, operationId?: string) => void;
  cancelCurrentOperation: () => void;
}

const SidebarContext = createContext<SidebarContextType | null>(null);

// Default flags
const DEFAULT_FLAGS: SidebarFlags = {
  show_sql: true,
  explain_generated_query: true,
  treat_empty_result_as_error: false,
  belt_and_suspenders: false,
};

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated } = useAuth();
  const { selectedWorkspace, fullWorkspaceData, isPostLoginInitialized } = useWorkspace();
  const [flags, setFlags] = useState<SidebarFlags>(DEFAULT_FLAGS);
  const [strategy, setStrategy] = useState<SqlGenerationStrategy>('Basic');
  const [isInitialized, setIsInitialized] = useState(false);
  const [isOperationInProgress, setIsOperationInProgress] = useState(false);
  const [currentOperationId, setCurrentOperationId] = useState<string | null>(null);

  // Post-login initialization of flags and strategy
  useEffect(() => {
    if (isAuthenticated && user && isPostLoginInitialized && !isInitialized) {
      // Use the aggregateGroupFlags function for proper OR logic
      const groupFlags = aggregateGroupFlags(user.group_profiles);
      
      // Create complete sidebar flags (treat_empty_result_as_error is always false by default, belt_and_suspenders from workspace)
      const initialFlags: SidebarFlags = {
        ...groupFlags,
        treat_empty_result_as_error: false,
        belt_and_suspenders: fullWorkspaceData?.belt_and_suspenders || false
      };
      
      setFlags(initialFlags);

      // Set SQL generation strategy from workspace level
      if (fullWorkspaceData) {
        const initialStrategy = convertWorkspaceLevelToStrategy(fullWorkspaceData.level);
        setStrategy(initialStrategy);
      }

      setIsInitialized(true);
    }
  }, [isAuthenticated, user, isPostLoginInitialized, fullWorkspaceData, isInitialized]);

  // Reset initialization when user logs out
  useEffect(() => {
    if (!isAuthenticated || !user) {
      setIsInitialized(false);
      setFlags(DEFAULT_FLAGS);
      setStrategy('Basic');
    }
  }, [isAuthenticated, user]);

  const updateFlag = useCallback((flag: keyof SidebarFlags, value: boolean) => {
    setFlags(prev => ({
      ...prev,
      [flag]: value,
    }));
  }, []);

  const updateStrategy = useCallback((newStrategy: SqlGenerationStrategy) => {
    setStrategy(newStrategy);
  }, []);

  const resetToDefaults = useCallback(() => {
    // Reset to the same values that were set during post-login initialization
    if (user && user.group_profiles) {
      const groupFlags = aggregateGroupFlags(user.group_profiles);
      const resetFlags: SidebarFlags = {
        ...groupFlags,
        treat_empty_result_as_error: false,
        belt_and_suspenders: fullWorkspaceData?.belt_and_suspenders || false
      };
      setFlags(resetFlags);

      // Reset strategy to workspace level default
      if (fullWorkspaceData) {
        const resetStrategy = convertWorkspaceLevelToStrategy(fullWorkspaceData.level);
        setStrategy(resetStrategy);
      } else {
        setStrategy('Basic');
      }
    } else {
      setFlags(DEFAULT_FLAGS);
      setStrategy('Basic');
    }
  }, [user, fullWorkspaceData]);

  // Operation tracking methods
  const setOperationInProgress = useCallback((inProgress: boolean, operationId?: string) => {
    setIsOperationInProgress(inProgress);
    if (inProgress && operationId) {
      setCurrentOperationId(operationId);
      // Debug logging in development only
      if (process.env.NODE_ENV === 'development') {
        console.log('[SidebarContext] Operation started:', operationId);
      }
    } else if (!inProgress) {
      setCurrentOperationId(null);
      // Debug logging in development only
      if (process.env.NODE_ENV === 'development') {
        console.log('[SidebarContext] Operation completed');
      }
    }
  }, []);

  const cancelCurrentOperation = useCallback(() => {
    // Debug logging in development only
    if (process.env.NODE_ENV === 'development') {
      console.log('[SidebarContext] Cancelling current operation:', currentOperationId);
    }
    
    // Cancel the API request
    const cancelled = sqlGeneratorApi.cancelCurrentRequest();
    
    // Reset operation state
    setIsOperationInProgress(false);
    setCurrentOperationId(null);
    
    // Emit a custom event for other components to listen to
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('operation-cancelled', { 
        detail: { operationId: currentOperationId, cancelled } 
      }));
    }
    
    return cancelled;
  }, [currentOperationId]);

  const value: SidebarContextType = {
    flags,
    strategy,
    isInitialized,
    isOperationInProgress,
    currentOperationId,
    updateFlag,
    updateStrategy,
    resetToDefaults,
    setOperationInProgress,
    cancelCurrentOperation,
  };

  return (
    <SidebarContext.Provider value={value}>
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
}