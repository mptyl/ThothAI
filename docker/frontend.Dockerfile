# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# === MULTI-STAGE BUILD FOR FRONTEND ===

# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependencies
COPY package*.json ./
RUN npm ci

# Copy source code in stages to ensure all directories are included
# First copy package files (already done above)
# Then copy configuration files
COPY tsconfig.json ./
COPY next.config.js ./
COPY postcss.config.js ./
COPY tailwind.config.js ./
COPY .eslintrc.json ./

# Copy all source directories explicitly
COPY app ./app
COPY components ./components
COPY lib ./lib
COPY public ./public

# Build arguments for public URLs
ARG NEXT_PUBLIC_DJANGO_SERVER
ARG NEXT_PUBLIC_SQL_GENERATOR_URL
ENV NEXT_PUBLIC_DJANGO_SERVER=$NEXT_PUBLIC_DJANGO_SERVER
ENV NEXT_PUBLIC_SQL_GENERATOR_URL=$NEXT_PUBLIC_SQL_GENERATOR_URL

# Create empty .env.local to prevent dotenv errors
RUN touch ../.env.local

# Build Next.js application
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME="0.0.0.0" \
    PORT=3000

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Copy production dependencies
COPY --from=deps /app/node_modules ./node_modules

# Copy entrypoint scripts
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
COPY entrypoint-frontend.sh /entrypoint.sh
RUN chmod +x /docker-entrypoint.sh /entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/logs /vol/secrets && \
    chown -R nextjs:nodejs /app && \
    chmod 700 /vol/secrets

# Switch to non-root user
USER nextjs

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/api/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

ENTRYPOINT ["/entrypoint.sh"]