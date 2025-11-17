// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { apiClient } from '@/lib/api';
import { Loader2 } from 'lucide-react';

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuth();
  const [isProcessing, setIsProcessing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleTokenAuth = async () => {
      const token = searchParams.get('token');
      
      if (!token) {
        // No token in URL, redirect based on auth status
        if (isAuthenticated) {
          router.replace('/chat');
        } else {
          router.replace('/login');
        }
        return;
      }

      try {
        // Set the token in the API client
        apiClient.setToken(token);
        
        // Verify the token is valid by testing it
        const isValid = await apiClient.testToken();
        
        if (isValid) {
          // Token is valid, fetch user info
          const user = await apiClient.getCurrentUser();
          
          if (user) {
            // Store user and token in localStorage (always use localStorage when coming from backend)
            localStorage.setItem('thoth_token', token);
            localStorage.setItem('thoth_user', JSON.stringify(user));
            localStorage.setItem('thoth_remember_me', 'true'); // Set remember me as the user is coming from backend
            
            // Force a page reload to update the auth context properly
            window.location.href = '/chat';
          } else {
            // Could not get user info, but token is valid
            // Store token anyway and redirect
            localStorage.setItem('thoth_token', token);
            localStorage.setItem('thoth_remember_me', 'true');
            window.location.href = '/chat';
          }
        } else {
          setError('Invalid token');
          setTimeout(() => router.replace('/login'), 2000);
        }
      } catch (err) {
        console.error('Error during token authentication:', err);
        setError('Authentication failed');
        setTimeout(() => router.replace('/login'), 2000);
      } finally {
        setIsProcessing(false);
      }
    };

    handleTokenAuth();
  }, [searchParams, router, isAuthenticated]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-2">{error}</p>
          <p className="text-sm text-gray-500">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex items-center gap-2">
        <Loader2 className="h-6 w-6 animate-spin" />
        <span>Authenticating with ThothAI...</span>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Loading...</span>
        </div>
      </div>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}