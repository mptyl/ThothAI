// Copyright (c) 2025 Marco Pancotti
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

'use client';

import React, { useState } from 'react';
import { ThumbsUp, Check, X } from 'lucide-react';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from './ui/dialog';

interface LikeButtonProps {
  enabled: boolean;
  workspaceId: number;
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

export function LikeButton({ enabled, workspaceId, onSuccess, onError }: LikeButtonProps) {
  const [showDialog, setShowDialog] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const handleLikeClick = () => {
    if (enabled) {
      setShowDialog(true);
    }
  };

  const handleConfirm = async () => {
    setIsSaving(true);
    
    try {
      const response = await fetch('/api/save-sql-feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workspace_id: workspaceId,
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to save feedback');
      }

      const result = await response.json();
      
      if (result.success) {
        setShowDialog(false);
        if (onSuccess) {
          onSuccess();
        }
      } else {
        throw new Error(result.error || 'Failed to save feedback');
      }
    } catch (error) {
      console.error('Error saving SQL feedback:', error);
      setShowDialog(false); // Close dialog even on error for better UX
      if (onError) {
        onError(error instanceof Error ? error.message : 'Failed to save feedback');
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setShowDialog(false);
  };

  return (
    <>
      <button
        type="button"
        onClick={handleLikeClick}
        disabled={!enabled}
        className={`
          p-2.5 rounded-xl transition-all
          ${enabled 
            ? 'text-white/70 hover:text-white hover:bg-primary/10 cursor-pointer' 
            : 'text-white/40 cursor-not-allowed'
          }
        `}
        title={enabled ? "Save this SQL as a good example" : "Generate a successful SQL query first"}
      >
        <ThumbsUp className="h-5 w-5" strokeWidth={2.5} />
      </button>

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="p-0 overflow-hidden">
          {/* Turquoise header with icon */}
          <div className="bg-gradient-to-r from-cyan-500 to-cyan-600 p-6 text-white">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-white/20 rounded-full backdrop-blur-sm">
                <ThumbsUp className="h-6 w-6" />
              </div>
              <DialogTitle className="text-xl font-bold text-white">
                Save This Result
              </DialogTitle>
            </div>
          </div>
          
          <div className="p-6">
            <DialogDescription className="text-base leading-relaxed">
              <div className="space-y-3">
                <p className="font-medium text-foreground">
                  Great! You&apos;ve found a useful answer.
                </p>
                <p>
                  Would you like to save this question and answer combination? 
                  This will help improve future responses by remembering successful queries like yours.
                </p>
                <div className="p-3 bg-cyan-50 dark:bg-cyan-950/30 rounded-lg border border-cyan-200 dark:border-cyan-800">
                  <p className="text-sm text-cyan-700 dark:text-cyan-300">
                    When you confirm, the system will store your question along with the generated answer 
                    to make similar future queries faster and more accurate.
                  </p>
                </div>
              </div>
            </DialogDescription>
            
            <DialogFooter className="pt-6 gap-3">
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={isSaving}
                className="flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X className="h-4 w-4" />
                Cancel
              </Button>
              <Button
                onClick={handleConfirm}
                disabled={isSaving}
                className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-600 hover:to-cyan-700 text-white border-0"
              >
                <Check className="h-4 w-4" />
                {isSaving ? 'Saving...' : 'OK, Remember!'}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}