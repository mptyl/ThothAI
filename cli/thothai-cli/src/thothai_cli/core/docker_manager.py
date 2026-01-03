# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Docker manager for container operations."""

import subprocess
from pathlib import Path
from typing import Optional
from rich.console import Console

from .config_manager import ConfigManager

console = Console()


class DockerManager:
    """Manages Docker operations for ThothAI."""
    
    def __init__(self, config_mgr: ConfigManager):
        self.config_mgr = config_mgr
        self.base_dir = config_mgr.config_path.parent
        self.compose_file = 'docker-compose.yml'
        # Used for remote deployments to track the target hostname
        self._remote_hostname: str | None = None

    def _extract_hostname_from_server(self, server: str) -> str:
        """Extract hostname from SSH URL.
        
        Args:
            server: SSH connection string (e.g., ssh://user@host or user@host)
            
        Returns:
            The hostname portion (e.g., 'host' or 'srv.example.com')
        """
        # Remove ssh:// prefix if present
        conn_str = server.replace('ssh://', '')
        
        # Split on @ to get user@host -> host
        if '@' in conn_str:
            hostname = conn_str.split('@', 1)[1]
        else:
            hostname = conn_str
        
        # Remove any trailing port (:22) if present
        if ':' in hostname:
            hostname = hostname.split(':')[0]
        
        return hostname

    def _create_nginx_files(self) -> bool:
        """Create custom nginx configuration files for server name support."""
        
        # Create custom nginx template (Always overwrite to ensure latest config)
        try:
            nginx_template_path = self.base_dir / '.nginx-custom.conf.tpl'
            template_content = """# Auto-generated nginx template with SERVER_NAME support
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
        return 200 "healthy\\n";
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
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
    
    # All other requests to Django
    location / {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        include /etc/nginx/proxy_params;
    }
}
"""
            nginx_template_path.write_text(template_content)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not create nginx template: {e}[/yellow]")

        # Create custom entrypoint script (Always overwrite)
        try:
            entrypoint_path = self.base_dir / '.nginx-custom-entrypoint.sh'
            entrypoint_content = """#!/bin/sh
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
"""
            entrypoint_path.write_text(entrypoint_content)
            entrypoint_path.chmod(0o755)
        except Exception as e:
             console.print(f"[yellow]Warning: Could not create nginx entrypoint: {e}[/yellow]")
        
        return True

    def _create_server_compose_file(self, remote_hostname: str | None = None) -> bool:
        """Create a custom docker-compose file with nginx configuration mounts.
        
        Args:
            remote_hostname: Optional hostname for remote deployments.
                             When provided, updates NEXT_PUBLIC_* variables to use
                             this hostname instead of localhost.
        """
        try:
            import yaml
            
            # Load original compose file
            if not (self.base_dir / self.compose_file).exists():
                return False

            with open(self.base_dir / self.compose_file) as f:
                compose_data = yaml.safe_load(f)
            
            # Modify proxy service
            if 'services' in compose_data and 'proxy' in compose_data['services']:
                proxy_service = compose_data['services']['proxy']
                
                # Ensure volumes exist
                if 'volumes' not in proxy_service:
                    proxy_service['volumes'] = []
                
                # Add nginx configuration mounts
                # We mount our custom template to the location where the container expects the template
                # AND we mount our entrypoint
                nginx_volumes = [
                    './.nginx-custom.conf.tpl:/etc/nginx/conf.d/default.conf.tpl:ro',
                    './.nginx-custom-entrypoint.sh:/custom-entrypoint.sh:ro'
                ]
                
                # Add volumes only if they don't exist
                for volume in nginx_volumes:
                    if volume not in proxy_service['volumes']:
                        proxy_service['volumes'].append(volume)
                
                # Add SERVER_NAME environment variable (only if not already present)
                if 'environment' not in proxy_service:
                    proxy_service['environment'] = []
                
                # Check if SERVER_NAME is already in env list
                has_server_name = False
                if isinstance(proxy_service['environment'], list):
                    has_server_name = any('SERVER_NAME' in str(env) for env in proxy_service['environment'])
                elif isinstance(proxy_service['environment'], dict):
                    has_server_name = 'SERVER_NAME' in proxy_service['environment']
                
                if not has_server_name:
                    if isinstance(proxy_service['environment'], list):
                        proxy_service['environment'].append('SERVER_NAME=${SERVER_NAME:-localhost}')
                    elif isinstance(proxy_service['environment'], dict):
                        proxy_service['environment']['SERVER_NAME'] = '${SERVER_NAME:-localhost}'
                
                # Add custom entrypoint
                proxy_service['entrypoint'] = ["/custom-entrypoint.sh"]
            
            # For remote deployments, update frontend NEXT_PUBLIC_* variables
            if remote_hostname and 'services' in compose_data and 'frontend' in compose_data['services']:
                frontend_service = compose_data['services']['frontend']
                if 'environment' not in frontend_service:
                    frontend_service['environment'] = []
                
                # Get ports from config
                ports = self.config_mgr.get('ports', {})
                web_port = ports.get('nginx', 8040)
                sql_gen_port = ports.get('sql_generator', 8020)
                
                # Define the new environment values for remote
                env_updates = {
                    'NEXT_PUBLIC_DJANGO_SERVER': f'http://{remote_hostname}:{web_port}',
                    'NEXT_PUBLIC_SQL_GENERATOR_URL': f'http://{remote_hostname}:{sql_gen_port}',
                    'RUNTIME_BACKEND_URL': f'http://{remote_hostname}:{web_port}',
                    'RUNTIME_SQL_GENERATOR_URL': f'http://{remote_hostname}:{sql_gen_port}',
                }
                
                # Update environment (handles both list and dict formats)
                if isinstance(frontend_service['environment'], list):
                    # Filter out old values and add new ones
                    new_env = []
                    for env in frontend_service['environment']:
                        key = env.split('=')[0] if '=' in str(env) else str(env)
                        if key not in env_updates:
                            new_env.append(env)
                    # Add the updated values
                    for key, value in env_updates.items():
                        new_env.append(f'{key}={value}')
                    frontend_service['environment'] = new_env
                elif isinstance(frontend_service['environment'], dict):
                    frontend_service['environment'].update(env_updates)
                    
                console.print(f"[dim]Updated frontend URLs to use {remote_hostname}[/dim]")
            
            # For remote deployments, update backend FRONTEND_URL
            if remote_hostname and 'services' in compose_data and 'backend' in compose_data['services']:
                backend_service = compose_data['services']['backend']
                if 'environment' not in backend_service:
                    backend_service['environment'] = []
                
                # Get frontend port from config
                ports = self.config_mgr.get('ports', {})
                frontend_port = ports.get('frontend', 3040)
                
                # Update FRONTEND_URL to use remote hostname
                frontend_url = f'http://{remote_hostname}:{frontend_port}'
                
                if isinstance(backend_service['environment'], list):
                    # Filter out old FRONTEND_URL and add new one
                    new_env = [env for env in backend_service['environment'] 
                               if not str(env).startswith('FRONTEND_URL=')]
                    new_env.append(f'FRONTEND_URL={frontend_url}')
                    backend_service['environment'] = new_env
                elif isinstance(backend_service['environment'], dict):
                    backend_service['environment']['FRONTEND_URL'] = frontend_url
                    
                console.print(f"[dim]Updated backend FRONTEND_URL to {frontend_url}[/dim]")
            
            # Write modified compose file
            with open(self.base_dir / '.docker-compose.server.yml', 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False)
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error creating server compose file: {e}[/red]")
            return False
    
    def _ensure_env_docker(self, remote_hostname: str | None = None) -> bool:
        """Ensure .env.docker exists and is up-to-date.
        
        Args:
            remote_hostname: Optional hostname for remote deployments.
                             Passed to generate_env_docker() for correct SERVER_NAME.
        """
        env_path = self.base_dir / '.env.docker'
        
        # Always regenerate to ensure it's current
        console.print("[dim]Generating .env.docker...[/dim]")
        if not self.config_mgr.generate_env_docker(remote_hostname=remote_hostname):
            console.print("[red]Failed to generate .env.docker[/red]")
            return False
        
        return True
    
    def _create_volumes(self, server: Optional[str] = None) -> bool:
        """Create required Docker volumes."""
        volumes = [
            'thoth-secrets',
            'thoth-backend-static',
            'thoth-backend-media',
            'thoth-frontend-cache',
            'thoth-qdrant-data',
            'thoth-shared-data',
            'thoth-data-exchange'
        ]
        
        console.print("[dim]Checking Docker volumes...[/dim]")
        
        for volume_name in volumes:
            result = self._run_cmd(
                ['docker', 'volume', 'ls', '--format', '{{.Name}}'],
                server=server,
                capture=True
            )
            
            if volume_name not in result.stdout.split('\n'):
                result = self._run_cmd(
                    ['docker', 'volume', 'create', volume_name],
                    server=server,
                    capture=True
                )
                if result.returncode != 0:
                    console.print(f"[red]Failed to create volume '{volume_name}'[/red]")
                    return False
        
        return True
    
    def _create_network(self, server: Optional[str] = None) -> bool:
        """Create Docker network if it doesn't exist."""
        network_name = 'thoth-network'
        
        result = self._run_cmd(
            ['docker', 'network', 'ls', '--format', '{{.Name}}'],
            server=server,
            capture=True
        )
        
        if network_name not in result.stdout.split('\n'):
            console.print(f"[dim]Creating network '{network_name}'...[/dim]")
            result = self._run_cmd(
                ['docker', 'network', 'create', network_name],
                server=server,
                capture=True
            )
            if result.returncode != 0:
                console.print(f"[red]Failed to create network[/red]")
                return False
        
        return True
    
    def check_connection(self, server: Optional[str] = None) -> bool:
        """Establish SSH connection and verify access.
        
        This also sets up the ControlMaster socket for subsequent commands
        to reuse the connection without re-authenticating.
        """
        if not server:
            return True
            
        console.print(f"[dim]Verifying connection to {server}...[/dim]")
        
        # We run a simple command to establish the connection.
        # We DO NOT capture output so the user can interactively enter password if needed.
        # This first connection creates the ControlMaster socket.
        ssh_cmd = [
            'ssh',
            '-o', 'ControlMaster=auto',
            '-o', 'ControlPath=~/.ssh/thothai-%C',
            '-o', 'ControlPersist=600',
            server,
            'echo "Connection established"'
        ]
        
        try:
            result = subprocess.run(ssh_cmd, text=True)
            if result.returncode == 0:
                return True
            else:
                console.print("[red]Failed to connect to server.[/red]")
                return False
        except Exception as e:
            console.print(f"[red]Connection error: {e}[/red]")
            return False

    def up(self, server: Optional[str] = None) -> bool:
        """Pull images and start containers."""
        # Establish connection first (handles auth once)
        if server and not self.check_connection(server):
            return False

        mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        if mode == 'swarm':
            return self.swarm_up(server=server)
        
        # Extract remote hostname for remote deployments
        remote_hostname = None
        if server:
            remote_hostname = self._extract_hostname_from_server(server)
            self._remote_hostname = remote_hostname
            console.print(f"[dim]Deploying to remote server: {remote_hostname}[/dim]")
            
        # Validate configuration
        console.print("[dim]Validating configuration...[/dim]")
        if not self.config_mgr.validate():
            return False
        
        # Generate .env.docker with correct SERVER_NAME
        if not self._ensure_env_docker(remote_hostname=remote_hostname):
            return False
            
        # Check for SERVER_NAME in .env.docker to trigger custom Nginx setup
        use_custom_compose = False
        env_docker_path = self.base_dir / '.env.docker'
        if env_docker_path.exists():
            with open(env_docker_path) as f:
                if 'SERVER_NAME=' in f.read():
                    console.print("[dim]Creating nginx configuration files for server name support...[/dim]")
                    if self._create_nginx_files():
                         if self._create_server_compose_file(remote_hostname=remote_hostname):
                             use_custom_compose = True
                             console.print("[dim]Using custom server configuration...[/dim]")
                    else:
                        console.print("[yellow]Warning: Failed to create nginx files, using defaults[/yellow]")

        # Create network and volumes
        if not self._create_network(server=server):
            return False
        if not self._create_volumes(server=server):
            return False
        
        # Pull images
        console.print("\n[bold]Pulling images from Docker Hub...[/bold]")
        result = self._run_cmd(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'pull'],
            server=server
        )
        
        if result.returncode != 0:
            console.print("[red]Failed to pull images[/red]")
            return False
        
        # Start containers
        console.print("\n[bold]Starting containers...[/bold]")
        # Note: Binder mounts don't work well over remote SSH with Docker Compose unless they exist on the target.
        # However, we are assuming the user knows what they are doing if they use --server with Compose.
        
        compose_file_to_use = '.docker-compose.server.yml' if use_custom_compose else self.compose_file
        
        # If using custom compose and deploying to remote server, we MUST copy the generated files
        if use_custom_compose and server:
             # Extract host/user from ssh connection string (ssh://user@host or user@host)
             remote_dest = server.replace('ssh://', '')
             
             console.print(f"[dim]Copying configuration files to remote server {remote_dest}...[/dim]")
             
             # Files to copy
             files_to_copy = [
                 '.nginx-custom.conf.tpl',
                 '.nginx-custom-entrypoint.sh',
                 '.docker-compose.server.yml'
             ]
             
             for filename in files_to_copy:
                 local_path = self.base_dir / filename
                 if local_path.exists():
                     # We assume the remote path mirrors the current directory structure if possible,
                     # OR simpler: copy to home directory or a temp dir?
                     # Docker Compose usually expects relative paths to work from where the compose file is.
                     # So if we copy docker-compose.server.yml to remote, we should put it in a folder 
                     # and run compose FROM THERE.
                     # BUT `docker -H ssh://... compose -f local_file up` uses the LOCAL file for definition,
                     # but mounts are relative to the REMOTE filesystem.
                     # So we need to put the mounted files on the remote filesystem at the SAME relative path 
                     # as defined in the compose file.
                     # The compose file says: `./.nginx-custom.conf.tpl`.
                     # So we need to put them in the "working directory" of the remote compose execution.
                     # When using `docker -H ... compose ...`, where is the "remote working directory"? 
                     # It doesn't really have one in the context of the host filesystem unless we specify it?
                     # Actually, `docker compose` resolves paths locally. So `./` becomes absolute local path?
                     # NO. `docker compose` sends the build context. But for bind mounts, it passes the path as is.
                     # If I run `docker -H ... compose -f file.yml up`, and file.yml has `./foo:/foo`, 
                     # Docker daemon receives absolute path of `./foo`?
                     # If I use `docker compose`, it converts relative paths to absolute paths ON THE CLIENT.
                     # So `/Users/mp/ThothAI/.nginx...` is sent to the remote daemon. The remote daemon looks for that path on the Linux server.
                     # Obviously that fails.
                     
                     # SOLUTION:
                     # We need to pick a stable path on the remote server, copy files there, 
                     # AND update the docker-compose file to point to those remote paths?
                     # OR simpler:
                     # Deploy to a specific folder on remote server (e.g. ~/thothai_deploy)
                     # and DO NOT use `docker -H ... compose -f local ...`.
                     # Instead, use `ssh remote "docker compose -f ... up"`.
                     # BUT `thothai-cli` is designed to run locally against remote daemon.
                     
                     # Compromise:
                     # 1. Copy files to `/tmp/thothai_config/` on remote server.
                     # 2. Modify the *local* `docker-compose.server.yml` (in memory or temp file) 
                     #    to point valid mounts to `/tmp/thothai_config/` instead of `./`.
                     # 3. Use that modified compose file to run against remote daemon.
                     
                     # Better yet:
                     # Just assume a standard deployment path on remote: `/opt/thothai` or `~/thothai`.
                     # Since we don't know the remote user's home easily without a query...
                     # `/tmp` is inconsistent across reboots.
                     
                     # Let's try to copy to `/tmp/thothai_deploy/` and use that for now.
                     # It's robust enough for a "fix".
                     
                     pass
        
        # ACTUALLY, simpler approach:
        # Just use scp to copy to a fixed path, say `/tmp/thothai_generated/`
        # And we need to Update the compose file we use to point to that.
        
        # Let's refine the logic.
        if use_custom_compose and server:
            remote_base_dir = "/tmp/thothai_generated"
            remote_dest_conn = server.replace('ssh://', '')
            
            # 1. Create remote directory
            self._run_cmd(['mkdir', '-p', remote_base_dir], server=server, capture=True)
            
            # 2. Copy files (nginx config, env, and config files needed by services)
            files_to_copy = [
                '.nginx-custom.conf.tpl', 
                '.nginx-custom-entrypoint.sh',
                '.env.docker',
                'config.yml.local'
            ]
            import shutil
            
            for f in files_to_copy:
                # Use scp command directly
                # scp local_file user@host:/tmp/thothai_generated/
                subprocess.run(['scp', str(self.base_dir / f), f"{remote_dest_conn}:{remote_base_dir}/{f}"], 
                             check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 3. Modify compose file locally to point to remote paths for bind mounts
            # We need to update paths that reference local files to use remote paths
            try:
                import yaml
                with open(self.base_dir / '.docker-compose.server.yml') as f:
                    data = yaml.safe_load(f)
                
                # Files that need path remapping
                files_to_remap = ['.nginx-custom.conf.tpl', '.nginx-custom-entrypoint.sh', 
                                  '.env.docker', 'config.yml.local']
                
                # Update volume mounts in ALL services
                for service_name, service_config in data.get('services', {}).items():
                    if 'volumes' not in service_config:
                        continue
                    
                    volumes = service_config.get('volumes', [])
                    new_volumes = []
                    for vol in volumes:
                        parts = vol.split(':')
                        if len(parts) >= 2:
                            src = parts[0]
                            filename = Path(src).name
                            # Check if this is a file we copied to remote
                            if filename in files_to_remap or any(f in src for f in files_to_remap):
                                # Replace with absolute remote path
                                new_src = f"{remote_base_dir}/{filename}"
                                parts[0] = new_src
                                new_volumes.append(':'.join(parts))
                            else:
                                new_volumes.append(vol)
                        else:
                            new_volumes.append(vol)
                    service_config['volumes'] = new_volumes
                
                # Save as temporary remote-ready compose file
                compose_file_to_use = '.docker-compose.server.remote.yml'
                with open(self.base_dir / compose_file_to_use, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False)
                    
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to prepare remote compose file: {e}[/yellow]")
        
        result = self._run_cmd(
            ['docker', 'compose', '-f', str(self.base_dir / compose_file_to_use), 'up', '-d'],
            server=server
        )
        
        if result.returncode != 0:
            console.print("[red]Failed to start containers[/red]")
            return False
        
        # Wait for backend and run initial setup
        if not self.wait_for_backend(server=server):
            return False
            
        if not self.run_initial_setup_commands(server=server):
            return False
        
        return True
    
    def down(self, server: Optional[str] = None) -> bool:
        """Stop and remove containers."""
        # Establish connection first
        if server and not self.check_connection(server):
            return False

        mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        if mode == 'swarm':
            return self.swarm_down(server=server)

        result = self._run_cmd(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'down'],
            server=server
        )
        
        return result.returncode == 0
    
    def status(self, server: Optional[str] = None) -> None:
        """Show container status."""
        # Establish connection first
        if server and not self.check_connection(server):
            return

        mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        if mode == 'swarm':
            self.swarm_status(server=server)
            return 

        self._run_cmd(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'ps'],
            server=server
        )
    
    def logs(self, service: Optional[str] = None, tail: int = 50, follow: bool = False, server: Optional[str] = None) -> None:
        """View container logs."""
        # Establish connection first
        if server and not self.check_connection(server):
            return

        mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        if mode == 'swarm':
            swarm_env = self._get_swarm_env()
            stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
            service_name = f"{stack_name}_{service}" if service else f"{stack_name}"
            cmd = ['docker', 'service', 'logs']
            if follow:
                cmd.append('-f')
            else:
                cmd.extend(['--tail', str(tail)])
            cmd.append(service_name)
            self._run_cmd(cmd, server=server)
            return

        cmd = ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'logs']
        
        if follow:
            cmd.append('-f')
        else:
            cmd.extend(['--tail', str(tail)])
        
        if service:
            cmd.append(service)
        
        self._run_cmd(cmd, server=server)
    
    def update(self, server: Optional[str] = None) -> bool:
        """Update containers to latest images."""
        # Establish connection first
        if server and not self.check_connection(server):
            return False

        mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        if mode == 'swarm':
            return self.swarm_update(server=server)

        # Ensure configuration is up-to-date
        if not self._ensure_env_docker():
            return False
        
        # Pull latest images
        console.print("\n[bold]Pulling latest images...[/bold]")
        result = self._run_cmd(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'pull'],
            server=server
        )
        
        if result.returncode != 0:
            console.print("[red]Failed to pull latest images[/red]")
            return False
        
        # Recreate containers
        console.print("\n[bold]Recreating containers...[/bold]")
        result = self._run_cmd(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'up', '-d', '--force-recreate'],
            server=server
        )
        
        if result.returncode != 0:
            console.print("[red]Failed to recreate containers[/red]")
            return False
        
        return True
    
    def _get_swarm_env(self) -> dict:
        """Get environment variables for Swarm deployment."""
        env = {}
        swarm_env_path = self.base_dir / 'swarm_config.env'
        if swarm_env_path.exists():
            with open(swarm_env_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env[key] = value
        
        # Add values from .env.docker if not present
        env_docker_path = self.base_dir / '.env.docker'
        if env_docker_path.exists():
            with open(env_docker_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        if key not in env:
                            env[key] = value
        
        return env

    def wait_for_backend(self, server: Optional[str] = None) -> bool:
        """Wait for backend container to be ready."""
        console.print("\n[dim]Waiting for backend to be ready...[/dim]")
        import time
        
        max_attempts = 30
        
        for i in range(max_attempts):
            result = self._run_cmd(
                ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'exec', '-T', 'backend', 
                 'python', '-c', 'print("ready")'],
                server=server,
                capture=True
            )
            if result.returncode == 0:
                console.print("[green]✓ Backend is ready[/green]")
                return True
            
            time.sleep(2)
            if i > 0 and i % 5 == 0:
                console.print(f"[dim]Still waiting... ({i}/{max_attempts})[/dim]")
        
        console.print("[yellow]Warning: Backend may not be fully ready[/yellow]")
        return True

    def run_initial_setup_commands(self, server: Optional[str] = None) -> bool:
        """Run initial setup commands for greenfield installation."""
        console.print("\n[bold]Checking for initial setup...[/bold]")
        
        # Check if this is a greenfield installation
        result = self._run_cmd(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'exec', '-T', 'backend', 'python', 
             '-c', 'import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Thoth.settings"); '
                   'import django; django.setup(); from thoth_core.models import Workspace; '
                   'print(Workspace.objects.count())'],
            server=server,
            capture=True
        )
        
        try:
            workspace_count = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else -1
        except ValueError:
            workspace_count = -1
        
        if workspace_count == 0:
            console.print("[bold blue]Greenfield installation detected. Running initial setup commands...[/bold blue]\n")
            
            # Check if any AI provider is configured
            providers = self.config_mgr.get('ai_providers', {})
            ai_configured = any(
                provider.get('enabled') and provider.get('api_key')
                for provider in providers.values()
            )
            
            if ai_configured:
                console.print("[dim]AI provider configured. Running automated analysis for demo database...[/dim]")
                
                # 1. Generate database scope
                console.print("[dim]1. Generating database scope...[/dim]")
                result = self._run_cmd(
                    ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'exec', '-T', 'backend', 
                     'python', 'manage.py', 'generate_db_scope_demo'],
                    server=server,
                    capture=True
                )
                if result.returncode == 0:
                    console.print("[green]✓ Database scope generated[/green]")
                else:
                    console.print("[yellow]⚠ Scope generation failed or skipped[/yellow]")
                
                # 2. Generate database documentation
                console.print("[dim]2. Generating database documentation...[/dim]")
                result = self._run_cmd(
                    ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'exec', '-T', 'backend',
                     'python', 'manage.py', 'generate_db_documentation_demo'],
                    server=server,
                    capture=True
                )
                if result.returncode == 0:
                    console.print("[green]✓ Database documentation generated[/green]")
                else:
                    console.print("[yellow]⚠ Documentation generation failed or skipped[/yellow]")
                
                # 3. Run GDPR scan
                console.print("[dim]3. Scanning for GDPR-sensitive data...[/dim]")
                result = self._run_cmd(
                    ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'exec', '-T', 'backend',
                     'python', 'manage.py', 'scan_gdpr_demo'],
                    server=server,
                    capture=True
                )
                if result.returncode == 0:
                    console.print("[green]✓ GDPR scan completed[/green]")
                else:
                    console.print("[yellow]⚠ GDPR scan failed or skipped[/yellow]")
                
                console.print("\n[bold green]✓ AI-assisted analysis completed[/bold green]")
            else:
                console.print("[yellow]No AI provider API keys configured.[/yellow]")
                console.print("Skipping automated scope, documentation, and GDPR scan.")
        elif workspace_count > 0:
            console.print("[dim]Found existing workspaces. Skipping initial setup.[/dim]")
        
        return True

    def _run_cmd(self, cmd: list, server: Optional[str] = None, capture: bool = False, env: Optional[dict] = None) -> subprocess.CompletedProcess:
        """Run a command locally or remotely via SSH."""
        import os
        
        # Prepare environment
        full_env = os.environ.copy()
        
        # Load .env.docker if it exists to ensure compose file variable substitution works
        env_docker_path = self.base_dir / '.env.docker'
        if env_docker_path.exists():
            try:
                from dotenv import dotenv_values
                docker_env = dotenv_values(env_docker_path)
                if docker_env:
                    clean_env = {k: v for k, v in docker_env.items() if v is not None}
                    full_env.update(clean_env)
            except ImportError:
                pass

        if env:
            full_env.update(env)

        if server and cmd[0] == 'docker':
            # For docker commands, use DOCKER_HOST to run against remote daemon with local files
            docker_host = server
            if not docker_host.startswith('ssh://'):
                 docker_host = f"ssh://{docker_host}"
            
            full_env['DOCKER_HOST'] = docker_host
            
            # Run without SSH wrapper, locally, but targeting remote daemon
            return subprocess.run(cmd, cwd=self.base_dir, capture_output=capture, text=True, env=full_env)
            
        elif server:
            # For non-docker commands (e.g. strict shell commands), use SSH wrapper
            ssh_cmd = [
                'ssh',
                '-o', 'ControlMaster=auto',
                '-o', 'ControlPath=~/.ssh/thothai-%C',
                '-o', 'ControlPersist=600',
                server,
                ' '.join(cmd)
            ]
            return subprocess.run(ssh_cmd, cwd=self.base_dir, capture_output=capture, text=True)
        else:
            return subprocess.run(cmd, cwd=self.base_dir, capture_output=capture, text=True, env=full_env)

    def _manage_swarm_resources(self, stack_name: str, server: Optional[str] = None) -> bool:
        """Create secrets, configs, and network for Swarm."""
        console.print("[dim]Managing Swarm secrets and configs...[/dim]")
        
        # Remove existing (best effort)
        self._run_cmd(['docker', 'secret', 'rm', f"{stack_name}_thoth_env_config", f"{stack_name}_thoth_config_yml"], server)
        self._run_cmd(['docker', 'config', 'rm', f"{stack_name}_thoth_env_docker"], server)
        
        # Create new
        res1 = self._run_cmd(['docker', 'secret', 'create', f"{stack_name}_thoth_env_config", '.env.docker'], server)
        res2 = self._run_cmd(['docker', 'secret', 'create', f"{stack_name}_thoth_config_yml", 'config.yml.local'], server)
        res3 = self._run_cmd(['docker', 'config', 'create', f"{stack_name}_thoth_env_docker", '.env.docker'], server)
        
        if res1.returncode != 0 or res2.returncode != 0 or res3.returncode != 0:
            console.print("[yellow]Warning: Some secrets or configs could not be created (they may already exist)[/yellow]")
            
        # Network is now created automatically by the stack (not external)
        # The stack YAML defines thoth-network with driver: overlay, attachable: true
        
        return True

    def swarm_up(self, server: Optional[str] = None) -> bool:
        """Deploy ThothAI to Docker Swarm."""
        # Extract remote hostname for remote deployments
        remote_hostname = None
        if server:
            remote_hostname = self._extract_hostname_from_server(server)
            self._remote_hostname = remote_hostname
            console.print(f"[dim]Deploying Swarm to remote server: {remote_hostname}[/dim]")
        
        if not self.config_mgr.validate():
            return False
        
        # Generate .env.docker with correct SERVER_NAME for remote
        if not self.config_mgr.generate_env_docker(remote_hostname=remote_hostname):
            return False
            
        # Strict check for swarm_config.env (no auto-generation)
        swarm_config_path = self.base_dir / 'swarm_config.env'
        if not swarm_config_path.exists():
            console.print("[red]Error: 'swarm_config.env' not found.[/red]")
            console.print("This file is required for Swarm deployment.")
            console.print("Please run [bold]thothai init --mode swarm[/bold] to generate it, or create it manually.")
            return False
            
        swarm_env = self._get_swarm_env()
        stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
        stack_file = self.config_mgr.get('docker', {}).get('stack_file', 'docker-stack.yml')
        
        # For remote deployments, inject NEXT_PUBLIC_* URLs with remote hostname
        if remote_hostname:
            ports = self.config_mgr.get('ports', {})
            web_port = ports.get('nginx', 8040)
            sql_gen_port = ports.get('sql_generator', 8020)
            
            # Add/override these in swarm_env for stack file substitution
            swarm_env['NEXT_PUBLIC_DJANGO_SERVER'] = f'http://{remote_hostname}:{web_port}'
            swarm_env['NEXT_PUBLIC_SQL_GENERATOR_URL'] = f'http://{remote_hostname}:{sql_gen_port}'
            swarm_env['RUNTIME_BACKEND_URL'] = f'http://{remote_hostname}:{web_port}'
            swarm_env['RUNTIME_SQL_GENERATOR_URL'] = f'http://{remote_hostname}:{sql_gen_port}'
            console.print(f"[dim]Updated Swarm frontend URLs to use {remote_hostname}[/dim]")
        
        if not (self.base_dir / stack_file).exists():
            console.print(f"[red]Error: Stack file '{stack_file}' not found[/red]")
            return False
            
        # Preprocess stack file to handle variable substitution in keys (which Docker doesn't support)
        # This replaces ${VAR} and ${VAR:-default} with values from swarm_env
        try:
            stack_content = (self.base_dir / stack_file).read_text(encoding='utf-8')
            processed_content = self._replace_env_vars(stack_content, swarm_env)
            
            # For remote deployments, replace localhost in NEXT_PUBLIC_* and RUNTIME_* URLs
            # This handles the template's "http://localhost:${WEB_PORT}" format
            if remote_hostname:
                import re
                # Replace localhost in env variable assignments that are for frontend URLs
                # Match patterns like "NEXT_PUBLIC_DJANGO_SERVER=http://localhost:" or similar
                for env_prefix in ['NEXT_PUBLIC_', 'RUNTIME_']:
                    pattern = rf'({env_prefix}[A-Z_]+=http://)localhost:'
                    replacement = rf'\1{remote_hostname}:'
                    processed_content = re.sub(pattern, replacement, processed_content)
            
            temp_stack_file = f"docker-stack.gen.yml"
            (self.base_dir / temp_stack_file).write_text(processed_content, encoding='utf-8')
            stack_file_to_deploy = temp_stack_file
        except Exception as e:
            console.print(f"[red]Error processing stack file: {e}[/red]")
            return False
            
        try:
            # Create volumes (Swarm usually uses local volumes if not configured otherwise, mimicking install-swarm.sh)
            volumes = ['thoth-secrets', 'thoth-backend-static', 'thoth-backend-media', 
                       'thoth-frontend-cache', 'thoth-qdrant-data', 'thoth-shared-data', 'thoth-data-exchange']
            for vol in volumes:
                self._run_cmd(['docker', 'volume', 'create', vol], server)
                
            # Manage secrets/configs
            self._manage_swarm_resources(stack_name, server)
            
            # Deploy stack
            console.print(f"\n[bold]Deploying stack '{stack_name}' to Swarm...[/bold]")
            result = self._run_cmd(
                ['docker', 'stack', 'deploy', '-c', stack_file_to_deploy, stack_name],
                server=server,
                env=swarm_env
            )
            
            if result.returncode != 0:
                console.print("[red]Failed to deploy stack[/red]")
                return False
            
            # Wait for all services to be healthy
            self.wait_for_swarm_services(stack_name, server)
            
            # Print access info
            self.print_access_info(is_swarm=True)
                
            return True
        finally:
            # Cleanup temp file
            if (self.base_dir / temp_stack_file).exists():
                (self.base_dir / temp_stack_file).unlink()
    
    def wait_for_swarm_services(self, stack_name: str, server: Optional[str] = None, timeout: int = 600) -> bool:
        """Wait for all Swarm services to be running.
        
        Args:
            stack_name: Name of the Docker stack
            server: Optional remote server for SSH execution
            timeout: Maximum time to wait in seconds (default 10 minutes)
            
        Returns:
            True if all services are healthy, False if timeout reached
        """
        import time
        
        console.print("\n[bold]Waiting for all services to be healthy...[/bold]")
        console.print("[dim]This may take several minutes on first install as the backend initializes...[/dim]")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self._run_cmd(
                ['docker', 'service', 'ls', '--filter', f'label=com.docker.stack.namespace={stack_name}', 
                 '--format', '{{.Replicas}}'],
                server=server,
                capture=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                replicas = result.stdout.strip().split('\n')
                all_healthy = True
                total_services = len(replicas)
                healthy_services = 0
                
                for replica in replicas:
                    if replica:
                        try:
                            current, desired = replica.split('/')
                            if current == desired and int(current) > 0:
                                healthy_services += 1
                            else:
                                all_healthy = False
                        except ValueError:
                            all_healthy = False
                
                if all_healthy and healthy_services == total_services:
                    console.print(f"[green]✓ All {total_services} services are running![/green]")
                    return True
                
                elapsed = int(time.time() - start_time)
                console.print(f"[dim]Services ready: {healthy_services}/{total_services} ({elapsed}s/{timeout}s)[/dim]")
            
            time.sleep(15)
        
        console.print("[yellow]Warning: Some services may still be starting. Check with 'thothai status'[/yellow]")
        return False

    def _replace_env_vars(self, content: str, env: dict) -> str:
        """Replace ${VAR} and ${VAR:-default} in content."""
        import re
        
        def replace(match):
            full_match = match.group(0)
            var_name = match.group(1)
            default_val = match.group(2)
            
            # If default_val starts with :-, remove it
            if default_val and default_val.startswith(':-'):
                default_val = default_val[2:]
            
            return env.get(var_name, default_val if default_val is not None else '')

        # Regex for ${VAR} or ${VAR:-default}
        pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)(:-[^}]*)?\}'
        return re.sub(pattern, replace, content)

    def swarm_down(self, server: Optional[str] = None) -> bool:
        """Remove ThothAI from Docker Swarm."""
        # Check if swarm_config.env exists
        swarm_config_path = self.base_dir / 'swarm_config.env'
        if not swarm_config_path.exists():
            console.print("[dim]Note: swarm_config.env not found, using default stack name 'thothai-swarm'[/dim]")
        
        swarm_env = self._get_swarm_env()
        stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
        
        console.print(f"\n[bold yellow]Removing stack '{stack_name}'...[/bold yellow]")
        result = self._run_cmd(['docker', 'stack', 'rm', stack_name], server, capture=True)
        
        if result.returncode != 0:
            # Show the error output
            if result.stderr:
                console.print(f"[red]{result.stderr.strip()}[/red]")
            if result.stdout:
                console.print(f"[dim]{result.stdout.strip()}[/dim]")
            return False
        
        # Show success message from docker
        if result.stdout:
            console.print(f"[dim]{result.stdout.strip()}[/dim]")
        
        # Cleanup secrets/configs after a short delay
        console.print("[dim]Cleaning up secrets and configs...[/dim]")
        import time
        time.sleep(2)
        self._run_cmd(['docker', 'secret', 'rm', f"{stack_name}_thoth_env_config", f"{stack_name}_thoth_config_yml"], server, capture=True)
        self._run_cmd(['docker', 'config', 'rm', f"{stack_name}_thoth_env_docker"], server, capture=True)
        
        return True

    def swarm_status(self, server: Optional[str] = None) -> None:
        """Show Swarm services status."""
        swarm_env = self._get_swarm_env()
        stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
        
        self._run_cmd(['docker', 'stack', 'services', stack_name], server)

    def swarm_update(self, server: Optional[str] = None) -> bool:
        """Update Swarm services to latest images."""
        return self.swarm_up(server)  # docker stack deploy handles updates

    def swarm_rollback(self, server: Optional[str] = None) -> bool:
        """Rollback Swarm services."""
        swarm_env = self._get_swarm_env()
        stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
        
        services_result = self._run_cmd(['docker', 'stack', 'services', '--format', '{{.Name}}', stack_name], server, capture=True)
        if services_result.returncode != 0:
            return False
            
        for service in services_result.stdout.strip().split('\n'):
            if service:
                console.print(f"Rolling back service {service}...")
                self._run_cmd(['docker', 'service', 'update', '--rollback', service], server)
        
        return True

    def print_access_info(self, is_swarm: bool = False) -> None:
        """Print access information."""
        ports = self.config_mgr.get('ports', {})
        admin = self.config_mgr.get('admin', {})
        
        web_port = ports.get('nginx', 8040)
        frontend_port = ports.get('frontend', 3040)
        
        if is_swarm:
            # Swarm might use different ports if specified in swarm_config.env
            swarm_env = self._get_swarm_env()
            web_port = swarm_env.get('WEB_PORT', web_port)
            frontend_port = swarm_env.get('FRONTEND_PORT', frontend_port)
        
        # Use remote hostname if set, otherwise localhost
        host = self._remote_hostname or 'localhost'
        
        console.print("\n[bold]Access URLs:[/bold]")
        console.print(f"  Main App:   http://{host}:{web_port}")
        console.print(f"  Frontend:   http://{host}:{frontend_port}")
        console.print(f"  Admin:      http://{host}:{web_port}/admin")
        
        console.print("\n[bold]Login Credentials:[/bold]")
        console.print(f"  Username: {admin.get('username', 'admin')}")
        console.print(f"  Password: [as configured in config.yml.local]")

    def swarm_logs(self, service: str = 'backend', tail: int = 50, follow: bool = False, server: Optional[str] = None) -> None:
        """View Swarm service logs."""
        swarm_env = self._get_swarm_env()
        stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
        
        # If the user passed a full service name (e.g., thothai-swarm_backend), use it.
        # Otherwise, assume it's a short name and prepend stack name.
        if service.startswith(stack_name + '_'):
             full_service_name = service
        else:
             full_service_name = f"{stack_name}_{service}"

        cmd = ['docker', 'service', 'logs']
        if follow:
            cmd.append('-f')
        else:
            cmd.extend(['--tail', str(tail)])
            
        cmd.append(full_service_name)
        
        self._run_cmd(cmd, server=server)
