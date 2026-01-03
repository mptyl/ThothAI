# Auto-generated nginx template with SERVER_NAME support
# Main web server on port 80 (Backend-only mode)
server {
    listen 80;
    server_name ${SERVER_NAME};
    
    # Static files
    location /static {
        alias /vol/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # Media files
    location /media {
        alias /vol/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # Export files
    location /exports {
        alias /vol/data_exchange/;
        autoindex on;
    }
    
    # Django admin
    location /admin {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
    
    # Backend Django API
    location /api {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Default: all other requests to Django backend
    location / {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
}

# Backend API on port 8040
server {
    listen 8040;
    server_name ${SERVER_NAME};
    
    # Static files
    location /static {
        alias /vol/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # Media files
    location /media {
        alias /vol/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # Export files
    location /exports {
        alias /vol/data_exchange/;
        autoindex on;
    }
    
    # Django admin with static files
    location /admin {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
    
    # API endpoints
    location /api {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
    
    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # All other requests to Django
    location / {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
}
