# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# === NGINX PROXY FOR UNIFIED THOTH ===

FROM nginx:alpine

# Install envsubst for template processing
RUN apk add --no-cache gettext

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration template
COPY default.conf.tpl /etc/nginx/conf.d/default.conf.tpl
COPY proxy_params /etc/nginx/proxy_params

# Copy startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Create necessary directories
RUN mkdir -p /vol/static /vol/media /vol/exports

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80 8040 3000 8001

CMD ["/start.sh"]