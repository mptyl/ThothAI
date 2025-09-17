# Main web server on port 80
server {
    listen 80;
    server_name localhost;
    
    # Static files
    location /static {
        alias /vol/static/;
        autoindex on;
    }
    
    # Export files
    location /exports {
        alias /vol/data_exchange/;
        autoindex on;
    }
    
    # Backend Django API
    location /api {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
    
    # Django admin
    location /admin {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Default to backend
    location / {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
}

# Backend API on port 8040
server {
    listen 8040;
    server_name localhost;
    
    # Static files - MUST be served by nginx
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

# Frontend on port 3000
server {
    listen 3000;
    server_name localhost;
    
    location / {
        proxy_pass http://${FRONTEND_HOST}:${FRONTEND_PORT};
        include /etc/nginx/proxy_params;
    }
}

# SQL Generator on port 8005
server {
    listen 8005;
    server_name localhost;
    
    location / {
        proxy_pass http://${SQL_GEN_HOST}:${SQL_GEN_PORT};
        include /etc/nginx/proxy_params;
    }
}