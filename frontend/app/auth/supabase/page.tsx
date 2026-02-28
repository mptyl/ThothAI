// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

/**
 * Pagina ricevitore per l'integrazione Athena → ThothAI.
 *
 * Flusso:
 *   1. Pagina si apre con URL pulita (nessun token)
 *   2. Segnala ad Athena "ready" via postMessage su window.opener
 *   3. Riceve il JWT Supabase da Athena via postMessage
 *   4. Valida l'origine del messaggio (NEXT_PUBLIC_ATHENA_ORIGIN)
 *   5. POST /api/supabase-auth per scambiare JWT → token Django
 *   6. Salva token Django in localStorage (schema identico al login nativo)
 *   7. Redirect a /chat
 *
 * Sicurezza: il JWT Supabase transita solo via postMessage e nel body
 * di una POST server-side — non compare mai in URL, log nginx, né Referer.
 *
 * Timeout: se Athena non risponde in 5s, redirect a /login.
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function SupabaseAuthPage() {
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'error'>('loading');

  useEffect(() => {
    const athenaOrigin =
      process.env.NEXT_PUBLIC_ATHENA_ORIGIN ?? 'http://localhost:3090';

    // Pagina aperta direttamente senza finestra padre: nessun token disponibile
    if (!window.opener) {
      router.replace('/login');
      return;
    }

    // Segnala ad Athena che la pagina è pronta a ricevere il token
    window.opener.postMessage('ready', athenaOrigin);

    const exchangeToken = async (supabaseToken: string) => {
      try {
        const res = await fetch('/api/supabase-auth', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: supabaseToken }),
        });

        if (!res.ok) throw new Error(`Auth failed: ${res.status}`);

        const { token: djangoToken, user } = await res.json();

        // Schema identico al login nativo ThothAI (vedi auth-context.tsx e api.ts)
        localStorage.setItem('thoth_token', djangoToken);
        localStorage.setItem('thoth_user', JSON.stringify(user));
        localStorage.setItem('thoth_remember_me', 'true');

        // Reload completo per reinizializzare AuthContext (stesso pattern di auth/callback)
        window.location.href = '/chat';
      } catch (err) {
        console.error('[supabase-auth] token exchange failed:', err);
        setStatus('error');
        setTimeout(() => router.replace('/login'), 2000);
      }
    };

    const handler = (event: MessageEvent) => {
      if (event.origin !== athenaOrigin) {
        console.warn(`[supabase-auth] Origin mismatch: ${event.origin} !== ${athenaOrigin}`);
        return;
      }
      if (event.data?.type !== 'supabase_token') {
        console.warn(`[supabase-auth] Expected type 'supabase_token', got '${event.data?.type}'`);
        return;
      }
      window.removeEventListener('message', handler);
      clearTimeout(timeoutId);
      const { token } = event.data;
      if (!token) {
        router.replace('/login');
        return;
      }
      exchangeToken(token);
    };

    window.addEventListener('message', handler);

    // Timeout di sicurezza: se Athena non risponde in 5s, redirect a /login
    const timeoutId = setTimeout(() => {
      window.removeEventListener('message', handler);
      setStatus('error');
      setTimeout(() => router.replace('/login'), 2000);
    }, 5000);

    return () => {
      window.removeEventListener('message', handler);
      clearTimeout(timeoutId);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (status === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-2">Autenticazione fallita.</p>
          <p className="text-sm text-gray-500">Reindirizzamento al login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex items-center gap-2">
        <Loader2 className="h-6 w-6 animate-spin" />
        <span>Autenticazione in corso...</span>
      </div>
    </div>
  );
}
