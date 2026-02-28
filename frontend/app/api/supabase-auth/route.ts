// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

/**
 * Next.js API route: POST /api/supabase-auth
 *
 * Proxy server-side tra il frontend ThothAI e il backend Django.
 * Riceve il JWT Supabase dal client e lo inoltra al backend Django
 * che lo valida via GoTrue e restituisce un token DRF.
 *
 * Il JWT Supabase non viene mai esposto in URL, log nginx, né header Referer:
 * transita solo nel body di richieste POST server→server.
 */

import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST(req: Request): Promise<Response> {
  let body: { token?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { token } = body;
  if (!token) {
    return NextResponse.json({ error: 'Token required' }, { status: 400 });
  }

  // backendUrl viene letto lato server — non esposto al browser
  const backendUrl = process.env.DJANGO_SERVER || process.env.RUNTIME_BACKEND_URL;
  if (!backendUrl) {
    console.error('[supabase-auth] DJANGO_SERVER / RUNTIME_BACKEND_URL not set');
    return NextResponse.json(
      { error: 'Backend URL not configured' },
      { status: 500 }
    );
  }

  const djangoAuthUrl = `${backendUrl}/api/supabase-auth`;

  try {
    const djangoRes = await fetch(djangoAuthUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });

    const data = await djangoRes.json();

    if (!djangoRes.ok) {
      return NextResponse.json(data, { status: djangoRes.status });
    }

    return NextResponse.json(data, { status: 200 });
  } catch (err) {
    console.error('[supabase-auth] Failed to contact Django backend:', err);
    return NextResponse.json(
      { error: 'Auth service unreachable' },
      { status: 503 }
    );
  }
}
