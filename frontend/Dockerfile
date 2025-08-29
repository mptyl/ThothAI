# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# ===== UNIVERSAL BUILD - Works on ALL architectures =====
# No compilation issues, optimized for multi-arch support
# Works on: Intel/AMD (x86_64), Apple Silicon (ARM64), Raspberry Pi (ARM)

FROM node:20

# Environment variables for universal compatibility
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME="0.0.0.0" \
    PORT=3000

WORKDIR /app

# Accept build arguments for configuration
ARG NEXT_PUBLIC_DJANGO_SERVER
ARG NEXT_PUBLIC_SQL_GENERATOR_URL

# Set build-time environment variables
ENV NEXT_PUBLIC_DJANGO_SERVER=$NEXT_PUBLIC_DJANGO_SERVER
ENV NEXT_PUBLIC_SQL_GENERATOR_URL=$NEXT_PUBLIC_SQL_GENERATOR_URL

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including dev) for the build phase
RUN npm ci && \
    npm cache clean --force

# Copy application code
COPY . .

# Build Next.js application
RUN npm run build

# Remove dev dependencies after build to reduce image size
RUN npm prune --production

# Create non-root user for security
RUN groupadd -r nodejs && \
    useradd -r -g nodejs -s /bin/false nextjs && \
    chown -R nextjs:nodejs /app

# Switch to non-root user
USER nextjs

EXPOSE 3000

# Use Next.js production server
CMD ["npm", "start"]