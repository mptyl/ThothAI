// Proxy route to forward streaming requests to the SQL Generator service

export const dynamic = 'force-dynamic';

export async function POST(req: Request): Promise<Response> {
  // Use SQL_GENERATOR_URL from environment (different for Docker vs local)
  const targetBaseUrl = process.env.SQL_GENERATOR_URL!;

  let payload: unknown;
  try {
    payload = await req.json();
  } catch (e) {
    return new Response('Invalid JSON body', { status: 400 });
  }

  const targetUrl = `${targetBaseUrl}/generate-sql`;

  // Extract username from headers if present
  const username = req.headers.get('X-Username');

  try {
    const requestHeaders: HeadersInit = {
      'Content-Type': 'application/json',
      Accept: 'text/plain',
    };
    
    // Forward username header if provided
    if (username) {
      requestHeaders['X-Username'] = username;
    }

    const controller = new AbortController();
    
    // Set up timeout for the upstream request
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, 120000); // 2 minutes timeout

    const upstream = await fetch(targetUrl, {
      method: 'POST',
      headers: requestHeaders,
      body: JSON.stringify(payload),
      // Disable Next.js request caching for streaming
      cache: 'no-store',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // If upstream request failed, return the error
    if (!upstream.ok) {
      const errorText = await upstream.text().catch(() => 'Unknown error');
      return new Response(errorText, { status: upstream.status });
    }

    // Create a TransformStream to handle the streaming response
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const reader = upstream.body?.getReader();

    if (!reader) {
      return new Response('No response body from upstream', { status: 502 });
    }

    // Process the stream in the background
    (async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          await writer.write(value);
        }
      } catch (error) {
        // Client disconnected or stream error - this is expected behavior
        // Debug logging in development only
        if (process.env.NODE_ENV === 'development') {
          console.log('Stream processing stopped:', error instanceof Error ? error.message : 'Unknown error');
        }
      } finally {
        try {
          await writer.close();
        } catch {
          // Writer already closed, ignore
        }
        try {
          reader.releaseLock();
        } catch {
          // Reader already released, ignore
        }
      }
    })();

    // Return the readable stream to the client
    const responseHeaders = new Headers();
    responseHeaders.set('Content-Type', 'text/plain');
    responseHeaders.set('Cache-Control', 'no-store');
    responseHeaders.set('X-Target-URL', targetBaseUrl);

    return new Response(readable, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error: any) {
    // Handle timeout and other errors
    if (error.name === 'AbortError') {
      return new Response('Request timeout - SQL generation took too long', { status: 504 });
    }
    
    const reason = error?.message || 'Unknown error';
    const message = `Proxy error contacting SQL Generator at ${targetBaseUrl}. Reason: ${reason}`;
    return new Response(message, { status: 502 });
  }
}


