// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import { useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Loader2 } from 'lucide-react';

function SSOCallbackContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const { loginWithToken } = useAuth();

    useEffect(() => {
        const token = searchParams.get('token');
        const next = searchParams.get('next') || '/chat';

        if (token) {
            loginWithToken(token)
                .then(() => {
                    console.log('[SSO] Authentication successful, redirecting to:', next);
                    router.push(next);
                })
                .catch((err) => {
                    console.error('[SSO] Callback error:', err);
                    router.push('/login?error=sso_failed');
                });
        } else {
            console.error('[SSO] No token received in callback');
            router.push('/login?error=no_token');
        }
    }, [searchParams, router, loginWithToken]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-background">
            <div className="flex items-center gap-4">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-lg text-muted-foreground">Completing authentication...</p>
            </div>
        </div>
    );
}

export default function SSOCallbackPage() {
    return (
        <Suspense fallback={
            <div className="flex flex-col items-center justify-center min-h-screen bg-background">
                <div className="flex items-center gap-4">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                    <p className="text-lg text-muted-foreground">Loading...</p>
                </div>
            </div>
        }>
            <SSOCallbackContent />
        </Suspense>
    );
}
