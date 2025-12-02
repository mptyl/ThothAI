// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Loader2, LogOut, AlertCircle } from 'lucide-react';

interface LogoutConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isLoggingOut?: boolean;
}

export function LogoutConfirmationDialog({
  open,
  onOpenChange,
  onConfirm,
  isLoggingOut = false,
}: LogoutConfirmationDialogProps) {
  const handleConfirm = () => {
    if (!isLoggingOut) {
      onConfirm();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <LogOut className="h-5 w-5" style={{ color: '#4a90a4' }} />
            Confirm Logout
          </DialogTitle>
          <DialogDescription className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" style={{ color: '#4a90a4' }} />
            <span>
              Are you sure you want to logout from ThothAI?
            </span>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-6 pt-4">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoggingOut}
            className="flex items-center gap-2"
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isLoggingOut}
            className="flex items-center gap-2 text-white font-semibold transition-all duration-300"
            style={{
              background: 'linear-gradient(135deg, #4a90a4, #5ba3b8)',
              border: '1px solid rgba(74, 144, 164, 0.3)',
              boxShadow: '0 4px 15px rgba(74, 144, 164, 0.4), 0 2px 4px rgba(0, 0, 0, 0.1)'
            }}
            onMouseEnter={(e) => {
              if (!isLoggingOut) {
                e.currentTarget.style.background = 'linear-gradient(135deg, #5ba3b8, #4a90a4)';
                e.currentTarget.style.boxShadow = '0 6px 25px rgba(74, 144, 164, 0.5), 0 3px 8px rgba(0, 0, 0, 0.15)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isLoggingOut) {
                e.currentTarget.style.background = 'linear-gradient(135deg, #4a90a4, #5ba3b8)';
                e.currentTarget.style.boxShadow = '0 4px 15px rgba(74, 144, 164, 0.4), 0 2px 4px rgba(0, 0, 0, 0.1)';
                e.currentTarget.style.transform = 'translateY(0px)';
              }
            }}
          >
            {isLoggingOut ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Logging out...
              </>
            ) : (
              <>
                <LogOut className="h-4 w-4" />
                Confirm Logout
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}