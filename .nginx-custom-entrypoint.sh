#!/bin/sh
set -e

# Wait for backend (simple sleep/check if needed, but usually compose handles startup order)
# Main goal: envsubst with SERVER_NAME

if [ -f /etc/nginx/conf.d/default.conf.tpl ]; then
    # We are using the mounted template which includes SERVER_NAME
    envsubst '$APP_HOST $APP_PORT $FRONTEND_HOST $FRONTEND_PORT $SQL_GEN_HOST $SQL_GEN_PORT $SERVER_NAME' < /etc/nginx/conf.d/default.conf.tpl > /etc/nginx/conf.d/default.conf
else
    # Fallback if something is wrong
    echo "Warning: Template not found at /etc/nginx/conf.d/default.conf.tpl"
fi

exec nginx -g "daemon off;"
