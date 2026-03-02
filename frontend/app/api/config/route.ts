import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
    // Read from server-side environment variables
    // In Docker Swarm, these are injected via 'environment' keys or .env files
    const backendUrl = process.env.RUNTIME_BACKEND_URL;
    const sqlGeneratorUrl = process.env.RUNTIME_SQL_GENERATOR_URL;
    const athenaOrigin = process.env.RUNTIME_ATHENA_ORIGIN;
    const athenaOriginsEnv = process.env.RUNTIME_ATHENA_ORIGINS;

    if (!backendUrl) {
        console.error('CRITICAL: RUNTIME_BACKEND_URL is not set in the environment');
        return NextResponse.json(
            { error: 'Configuration Missing: RUNTIME_BACKEND_URL' },
            { status: 500 }
        );
    }

    const athenaOrigins: string[] = athenaOriginsEnv
        ? athenaOriginsEnv.split(',').map(o => o.trim()).filter(Boolean)
        : [athenaOrigin || 'http://localhost:3090'];

    return NextResponse.json({
        backendUrl,
        sqlGeneratorUrl: sqlGeneratorUrl || backendUrl,
        athenaOrigin: athenaOrigin || '',
        athenaOrigins,
    });
}
