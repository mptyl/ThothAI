# Root "/" routing: browser requests → Django (backend home),
# Next.js RSC data fetches (RSC: 1 header) → frontend.
map $http_rsc $root_upstream {
    ""      http://${APP_HOST}:${APP_PORT};
    default http://${FRONTEND_HOST}:${FRONTEND_PORT};
}

# Unified server on port 80 (exposed as $THOTH_WEB_PORT, default 8040)
# Routes API/admin to Django backend, everything else to Next.js frontend.
# Works in both dev mode (frontend container) and after assembly (Django serves static export).
server {
    listen 80;
    server_name $SERVER_NAME;

    large_client_header_buffers 4 32k;

    # Needed because location = / uses a variable ($root_upstream) in proxy_pass,
    # which forces nginx to resolve hostnames at request time instead of startup.
    resolver 127.0.0.11 valid=30s;

    # Static files - served directly by nginx
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

    # Django admin, VDB pages, workspace selector, AJAX + SSO callback
    location /admin {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
    location /vdb {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
    location /set-workspace {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
    location /ajax {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
    location /auth/admin-callback {
        # Frontend sidebar hardcodes next=/admin/; override to "/" so the
        # SSO callback redirects to the backend home page instead of admin.
        set $args "token=$arg_token&next=/";
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }

    # Next.js frontend API routes (must come before the Django /api catch-all)
    location /api/config          { proxy_pass http://${FRONTEND_HOST}:${FRONTEND_PORT}; include /etc/nginx/proxy_params; }
    # /api/supabase-auth is handled by Django directly (falls through to /api catch-all).
    # Do NOT route it to the frontend: the frontend API route would call DJANGO_SERVER/api/supabase-auth
    # through this proxy, creating an infinite loop (frontend → proxy → frontend → …).
    location /api/sql-proxy       { proxy_pass http://${FRONTEND_HOST}:${FRONTEND_PORT}; include /etc/nginx/proxy_params; }
    location /api/save-sql-feedback { proxy_pass http://${FRONTEND_HOST}:${FRONTEND_PORT}; include /etc/nginx/proxy_params; }
    location /api/transcribe      { proxy_pass http://${FRONTEND_HOST}:${FRONTEND_PORT}; include /etc/nginx/proxy_params; }

    # Backend Django API (all other /api/* paths)
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

    # Exact root "/" → Django home for browser, frontend for RSC fetches
    location = / {
        proxy_pass $root_upstream;
        include /etc/nginx/proxy_params;
    }

    # All other requests to Next.js frontend (auth pages, dashboard, etc.)
    location / {
        proxy_pass http://${FRONTEND_HOST}:${FRONTEND_PORT};
        include /etc/nginx/proxy_params;

        # Dynamically resolve the sidebar "Athena" link to the origin the user
        # came from.  Athena passes ?athena_origin=<origin> when opening ThothAI;
        # the injected script:
        #   1. Stores athena_origin in localStorage (shared across all ThothAI tabs)
        #   2. Monkey-patches fetch() to override athenaOrigin in /api/config responses
        #      (so the useAthenaOrigin hook picks up the correct value)
        #   3. Overrides the "Athena" sidebar link click to focus the opener tab
        #      (window.opener.focus) instead of opening a new tab
        # Force uncompressed from upstream so sub_filter can match </head>.
        # gzip re-compresses for the client.
        proxy_set_header Accept-Encoding "";
        gzip on;
        gzip_types text/html application/javascript text/css application/json;
        sub_filter_once on;
        sub_filter_types text/html;
        sub_filter '</head>' '<script>(function(){var p=new URLSearchParams(location.search),o=p.get("athena_origin");if(o)localStorage.setItem("thoth_athena_origin",o);var s=localStorage.getItem("thoth_athena_origin");if(!s)return;var _f=window.fetch;window.fetch=function(u){var r=_f.apply(this,arguments);if(typeof u==="string"&&u.indexOf("/api/config")!==-1){return r.then(function(resp){return resp.text().then(function(t){try{var j=JSON.parse(t);j.athenaOrigin=s;return new Response(JSON.stringify(j),{status:resp.status,statusText:resp.statusText,headers:resp.headers})}catch(e){return new Response(t,{status:resp.status,statusText:resp.statusText,headers:resp.headers})}})})}return r};function f(){document.querySelectorAll("a[target=_blank]").forEach(function(a){if(a.textContent.trim()==="Athena"&&!a.dataset.p){a.href=s;a.dataset.p="1";a.addEventListener("click",function(e){e.preventDefault();e.stopPropagation();if(window.opener&&!window.opener.closed){window.opener.focus();try{window.close()}catch(x){}}else{window.location.href=s}})}})}new MutationObserver(f).observe(document.documentElement,{childList:true,subtree:true})})()</script></head>';
    }
}

# Frontend on port 3000 (direct access, used by thoth-frontend container port)
server {
    listen 3000;
    server_name $SERVER_NAME;

    location / {
        proxy_pass http://${FRONTEND_HOST}:${FRONTEND_PORT};
        include /etc/nginx/proxy_params;
    }
}

# SQL Generator on port 8005
server {
    listen 8005;
    server_name $SERVER_NAME;

    location / {
        proxy_pass http://${SQL_GEN_HOST}:${SQL_GEN_PORT};
        include /etc/nginx/proxy_params;
    }
}
