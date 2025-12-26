#!/bin/sh

set -e


# Wait for dependent services to be resolvable
for host in "$APP_HOST" "$FRONTEND_HOST" "$SQL_GEN_HOST"; do
    if [ -n "$host" ]; then
        echo "Waiting for $host to be resolvable..."
        while ! nslookup "$host" >/dev/null 2>&1; do
            echo "  $host not yet ready, retrying in 1s..."
            sleep 1
        done
        echo "$host is ready."
    fi
done

envsubst '$APP_HOST $APP_PORT $FRONTEND_HOST $FRONTEND_PORT $SQL_GEN_HOST $SQL_GEN_PORT' < /etc/nginx/conf.d/default.conf.tpl > /etc/nginx/conf.d/default.conf

nginx -g "daemon off;"
