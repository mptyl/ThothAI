// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Loader2 } from 'lucide-react';

function HomePageContent() {
  const { isAuthenticated, isLoading, loginWithToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Check if there's a token in the URL (SSO from backend)
    const token = searchParams.get('token');
    
    if (token) {
      // Use the new loginWithToken method to authenticate
      loginWithToken(token)
        .then(() => {
          // Successfully authenticated, redirect to chat
          router.replace('/chat');
        })
        .catch(() => {
          // Failed to authenticate with token, redirect to login
          router.replace('/login');
        });
      return;
    }

    // Normal flow if no SSO token
    if (!isLoading) {
      if (isAuthenticated) {
        router.replace('/chat');
      } else {
        router.replace('/login');
      }
    }
  }, [isAuthenticated, isLoading, router, searchParams, loginWithToken]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex items-center gap-2">
        <Loader2 className="h-6 w-6 animate-spin" />
        <span>Loading ThothAI...</span>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Loading ThothAI...</span>
        </div>
      </div>
    }>
      <HomePageContent />
    </Suspense>
  );
}