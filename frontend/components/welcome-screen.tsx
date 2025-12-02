// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/theme-toggle';
import { useAuth } from '@/lib/auth-context';
import { LogoutConfirmationDialog } from '@/components/logout-confirmation-dialog';
import { LogOut, Database, MessageSquare, Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export function WelcomeScreen() {
  const { user, logout, isLoading } = useAuth();
  const router = useRouter();
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);

  const handleLogoutClick = () => {
    setShowLogoutDialog(true);
  };

  const handleConfirmLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const handleStartChatting = () => {
    router.push('/chat');
  };

  return (
    <div className="welcome-container">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-center border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Sparkles className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">ThothAI</h1>
            <p className="text-sm text-muted-foreground">Natural Language to SQL</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button
            variant="ghost"
            onClick={handleLogoutClick}
            className="flex items-center gap-2 px-3"
            title="Logout from ThothAI"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline text-sm">Logout</span>
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center px-8 max-w-2xl mx-auto text-center">
        <div className="mb-8">
          <div className="mb-6 p-4 rounded-full bg-primary/10 inline-block">
            <Database className="h-12 w-12 text-primary" />
          </div>
          
          <h2 className="text-4xl font-bold mb-4">
            Welcome to ThothAI, {user?.first_name || user?.username}!
          </h2>
          
          <p className="text-xl text-muted-foreground mb-8 leading-relaxed">
            Transform your natural language questions into precise SQL queries using the power of AI.
            Get started by asking questions about your databases in plain English.
          </p>
        </div>

        {/* Features Preview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-3xl mb-12">
          <div className="p-6 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
            <MessageSquare className="h-8 w-8 text-primary mb-3" />
            <h3 className="font-semibold mb-2">Natural Language</h3>
            <p className="text-sm text-muted-foreground">
              Ask questions in plain English and get accurate SQL queries
            </p>
          </div>
          
          <div className="p-6 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
            <Database className="h-8 w-8 text-primary mb-3" />
            <h3 className="font-semibold mb-2">Multi-Database</h3>
            <p className="text-sm text-muted-foreground">
              Support for PostgreSQL, MySQL, SQLite, and more
            </p>
          </div>
          
          <div className="p-6 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
            <Sparkles className="h-8 w-8 text-primary mb-3" />
            <h3 className="font-semibold mb-2">AI-Powered</h3>
            <p className="text-sm text-muted-foreground">
              PydanticAI agents and vector search for intelligent query generation
            </p>
          </div>
        </div>

        {/* Getting Started */}
        <div className="w-full max-w-md">
          <Button size="lg" className="w-full mb-4" onClick={handleStartChatting}>
            Start Chatting
          </Button>
          <p className="text-sm text-muted-foreground">
            Begin your natural language to SQL conversation
          </p>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 text-center text-sm text-muted-foreground border-t border-border">
        <div className="space-y-2">
          <p>Copyright © 2025 Tyl Consulting - powered by CHESS (Talaei, Shayan and Pourreza, Mohammadreza and Chang, Yu-Chen and Mirhoseini, Azalia and Saberi, Amin). All rights reserved.</p>
          <p className="text-xs">
            Powered by Next.js • Django • PydanticAI • Qdrant
          </p>
          <p className="text-xs opacity-70">ThothAI UI v0.1.0</p>
        </div>
      </div>

      {/* Logout Confirmation Dialog */}
      <LogoutConfirmationDialog
        open={showLogoutDialog}
        onOpenChange={setShowLogoutDialog}
        onConfirm={handleConfirmLogout}
        isLoggingOut={isLoading}
      />
    </div>
  );
}