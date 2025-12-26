import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
    // Read from server-side environment variables
    // In Docker Swarm, these are injected via 'environment' keys or .env files
    const backendUrl = process.env.RUNTIME_BACKEND_URL;
    const sqlGeneratorUrl = process.env.RUNTIME_SQL_GENERATOR_URL;

    if (!backendUrl) {
        console.error('CRITICAL: RUNTIME_BACKEND_URL is not set in the environment');
        return NextResponse.json(
            { error: 'Configuration Missing: RUNTIME_BACKEND_URL' },
            { status: 500 }
        );
    }

    return NextResponse.json({
        backendUrl,
        sqlGeneratorUrl: sqlGeneratorUrl || backendUrl, // Fallback if needed
    });
}
