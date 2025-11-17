// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React, { useState } from 'react';
import { RefreshCw, Loader2 } from 'lucide-react';
import { useSidebar } from '@/lib/contexts/sidebar-context';
import { toast } from 'sonner';

export function ResetButton() {
  const { 
    cancelCurrentOperation, 
    isOperationInProgress,
    resetToDefaults 
  } = useSidebar();
  const [isCancelling, setIsCancelling] = useState(false);

  const handleReset = async () => {
    // Debug logging in development only
    if (process.env.NODE_ENV === 'development') {
      console.log('[ResetButton] Reset clicked, operation in progress:', isOperationInProgress);
    }
    
    setIsCancelling(true);
    
    try {
      // If an operation is in progress, cancel it first
      if (isOperationInProgress) {
        // Debug logging in development only
        if (process.env.NODE_ENV === 'development') {
          console.log('[ResetButton] Cancelling ongoing operation...');
        }
        cancelCurrentOperation();
        toast.info('Operation cancelled');
      }
      
      // Reset sidebar to defaults
      resetToDefaults();
      
      // Clear any other application state by emitting a global reset event
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('app-reset'));
      }
      
      // Debug logging in development only
      if (process.env.NODE_ENV === 'development') {
        console.log('[ResetButton] Reset complete');
      }
      toast.success('Reset complete');
      
    } catch (error) {
      console.error('[ResetButton] Error during reset:', error);
      toast.error('Reset failed');
    } finally {
      // Add a small delay to show the animation
      setTimeout(() => {
        setIsCancelling(false);
      }, 300);
    }
  };

  return (
    <button
      onClick={handleReset}
      disabled={isCancelling}
      className={`
        w-full py-2 px-4 rounded text-sm font-medium transition-all duration-200 
        flex items-center justify-center space-x-2
        ${isCancelling 
          ? 'bg-orange-600 text-white cursor-not-allowed' 
          : isOperationInProgress
            ? 'bg-red-600 hover:bg-red-700 text-white'
            : 'bg-gray-800 hover:bg-gray-700 text-white'
        }
      `}
      title={isOperationInProgress ? 'Cancel current operation and reset' : 'Reset to defaults'}
    >
      {isCancelling ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <RefreshCw className="h-4 w-4" />
      )}
      <span>
        {isCancelling 
          ? 'Cancelling...' 
          : isOperationInProgress 
            ? 'Cancel & Reset' 
            : 'Reset'
        }
      </span>
    </button>
  );
}