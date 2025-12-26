/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: [],
  },
  images: {
    domains: ['localhost'],
  },
  // Only use standalone output for production builds (Docker)
  ...(process.env.NODE_ENV === 'production' && { output: 'standalone' }),
  async rewrites() {
    return [
      {
        source: '/console/chat',
        destination: '/chat',
      },
    ]
  },
}

module.exports = nextConfig