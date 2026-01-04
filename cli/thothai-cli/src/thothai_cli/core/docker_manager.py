# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Docker manager for container operations."""

import subprocess
import os
import hashlib
import time
import signal
import atexit
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
        self._tunnel_process: Optional[subprocess.Popen] = None
        self._tunnel_socket: Optional[Path] = None
        # Docker Context tracking
        self._active_docker_context: str | None = None
        self._previous_docker_context: str | None = None
        
        # Register cleanup on exit
        atexit.register(self._stop_ssh_tunnel)

    def _get_server_hash(self, server: str) -> str:
        """Generate a unique hash for the server connection."""
        return hashlib.md5(server.encode()).hexdigest()[:8]

    def _get_tunnel_paths(self, server: str) -> tuple[Path, Path]:
        """Get paths for tunnel socket and PID file."""
        s_hash = self._get_server_hash(server)
        socket_path = Path(f"/tmp/thothai-docker-{s_hash}.sock")
        pid_path = Path(f"/tmp/thothai-docker-{s_hash}.pid")
        return socket_path, pid_path

    def _start_ssh_tunnel(self, server: str) -> str | None:
        """Start a background SSH tunnel for the Docker socket."""
        # Clean connection string (strip ssh:// if present)
        # OpenSSH 'ssh' command doesn't always like the ssh:// prefix
        clean_server = server.replace('ssh://', '')
        
        socket_path, pid_path = self._get_tunnel_paths(clean_server)
        
        # If socket exists, try to see if it's alive
        if socket_path.exists():
            try:
                # Test connection to the socket
                test_cmd = ['docker', '-H', f'unix://{socket_path}', 'version', '--format', '{{.Client.Version}}']
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self._tunnel_socket = socket_path
                    return str(socket_path)
            except Exception:
                pass
            
            # If not alive or failed, remove it
            try:
                socket_path.unlink()
            except Exception:
                pass

        console.print(f"[dim]Establishing secure tunnel to {server}...[/dim]")
        
        # Determine a safe ControlPath
        # Some systems might not have ~/.ssh/ or it might have permission issues
        ssh_dir = Path.home() / '.ssh'
        if ssh_dir.exists() and os.access(ssh_dir, os.W_OK):
            control_path = '~/.ssh/thothai-%C'
        else:
            control_path = f'/tmp/thothai-{hashlib.md5(clean_server.encode()).hexdigest()[:8]}-%C'

        # Start SSH tunnel in background
        # -nN: No stdin, No command execution
        # -L: Local socket to remote socket
        # -o ControlMaster=auto ...: Standard OpenSSH multiplexing
        ssh_cmd = [
            'ssh', '-nN',
            '-L', f'{socket_path}:/var/run/docker.sock',
            '-o', 'ControlMaster=auto',
            '-o', 'ControlPath=' + control_path,
            '-o', 'ControlPersist=600',
            clean_server
        ]
        
        try:
            # We don't use -f because we want to manage the process ourselves via Popen
            # to ensure we can kill it if needed, OR we can use the pid file.
            process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait for socket to appear
            start_time = time.time()
            while time.time() - start_time < 15:
                if socket_path.exists():
                    self._tunnel_process = process
                    self._tunnel_socket = socket_path
                    # Save PID for cleanup
                    pid_path.write_text(str(process.pid))
                    return str(socket_path)
                
                if process.poll() is not None:
                    # SSH exited early (e.g. auth failed)
                    stdout, stderr = process.communicate()
                    error_msg = stderr.strip() or stdout.strip() or "Process exited with code " + str(process.returncode)
                    
                    if "Permission denied" in error_msg:
                        console.print("[red]SSH Permission denied. Check your keys or password.[/red]")
                    else:
                        console.print(f"[red]SSH tunnel failed: {error_msg}[/red]")
                    return None
                    
                time.sleep(0.5)
            
            console.print("[red]Timeout waiting for SSH tunnel socket[/red]")
            # Try to get any error message before terminating
            if process.poll() is None:
                process.terminate()
                stdout, stderr = process.communicate(timeout=1)
                if stderr.strip():
                    console.print(f"[red]SSH error: {stderr.strip()}[/red]")
            
            return None
            
        except Exception as e:
            console.print(f"[red]Error creating SSH tunnel: {e}[/red]")
            return None

    def _parse_ssh_url(self, server: str) -> tuple[str, str, int]:
        """Parse SSH URL into user, host, port."""
        clean_server = server.replace('ssh://', '')
        user = ''
        port = 22
        
        # Extract user
        if '@' in clean_server:
            user, clean_server = clean_server.split('@', 1)
            user += '@' # Include @ for easy concatenation
        
        # Extract port
        if ':' in clean_server:
            host, port_str = clean_server.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                pass
            clean_server = host
            
        return user, clean_server, port


    def _stop_ssh_tunnel(self):
        """Stop the background SSH tunnel."""
        if self._tunnel_process:
            try:
                self._tunnel_process.terminate()
                self._tunnel_process.wait(timeout=2)
            except Exception:
                self._tunnel_process.kill()
            self._tunnel_process = None

        if self._tunnel_socket and self._tunnel_socket.exists():
            try:
                self._tunnel_socket.unlink()
            except Exception:
                pass
            
            # Also clean up PID file
            pid_path = self._tunnel_socket.with_suffix('.pid')
            if pid_path.exists():
                pid_path.unlink()
        
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

    # =============================
    # Docker Context Methods
    # =============================
    
    def _use_docker_context(self, server: str) -> tuple[bool, str]:
        """Use Docker Context for remote connection.
        
        Creates and activates a Docker Context for the specified server,
        enabling transparent remote Docker commands via SSH.
        
        Args:
            server: SSH connection string (e.g., user@host or ssh://user@host)
            
        Returns:
            Tuple of (success, previous_context_name)
        """
        user, host, port = self._parse_ssh_url(server)
        clean_server = f"{user}{host}"
        if port != 22:
             clean_server = f"{clean_server}:{port}"
             
        context_name = f"thothai-{self._get_server_hash(clean_server)}"
        
        console.print(f"[dim]Using Docker Context: {context_name}[/dim]")
        
        # Check if context already exists
        result = subprocess.run(
            ['docker', 'context', 'ls', '--format', '{{.Name}}'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[yellow]Warning: Could not list Docker contexts: {result.stderr}[/yellow]")
            return False, ""
        
        existing_contexts = result.stdout.strip().split('\n')
        
        if context_name not in existing_contexts:
            console.print(f"[dim]Creating Docker Context for {clean_server}...[/dim]")
            
            create_cmd = [
                'docker', 'context', 'create', context_name,
                '--docker', f'host=ssh://{clean_server}'
            ]
            
            result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[yellow]Warning: Could not create Docker Context: {result.stderr}[/yellow]")
                return False, ""
            
            console.print(f"[green]✓ Docker Context created[/green]")
        else:
            console.print(f"[dim]Docker Context already exists[/dim]")
        
        # Save current context to restore later
        result = subprocess.run(
            ['docker', 'context', 'show'],
            capture_output=True,
            text=True
        )
        previous_context = result.stdout.strip() if result.returncode == 0 else "default"
        
        # Activate the context
        result = subprocess.run(
            ['docker', 'context', 'use', context_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[red]Error: Could not use Docker Context: {result.stderr}[/red]")
            return False, ""
        
        console.print(f"[green]✓ Using Docker Context: {context_name}[/green]")
        
        # Store context info for later restoration
        self._active_docker_context = context_name
        self._previous_docker_context = previous_context
        
        return True, previous_context

    def _restore_docker_context(self, previous_context: str) -> bool:
        """Restore the previous Docker Context.
        
        Args:
            previous_context: Name of the context to restore
            
        Returns:
            True if restoration succeeded
        """
        if not previous_context:
            previous_context = "default"
        
        console.print(f"[dim]Restoring Docker Context: {previous_context}[/dim]")
        
        result = subprocess.run(
            ['docker', 'context', 'use', previous_context],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[yellow]Warning: Could not restore Docker Context: {result.stderr}[/yellow]")
            return False
        
        self._active_docker_context = None
        console.print(f"[green]✓ Docker Context restored[/green]")
        return True

    def _rsync_files(self, server: str, remote_dir: str = "/opt/thothai") -> bool:
        """Transfer required files to remote server using rsync.
        
        Uses rsync for efficient incremental transfers (delta-transfer algorithm).
        
        Args:
            server: SSH connection string
            remote_dir: Remote directory path for deployment files
            
        Returns:
            True if all transfers succeeded
        """
        user, host, port = self._parse_ssh_url(server)
        clean_server = f"{user}{host}"
        
        console.print(f"[dim]Syncing files to {clean_server}:{remote_dir}...[/dim]")
        
        # SSH options for robustness
        ssh_opts = f"ssh -p {port} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        
        # Create remote directory
        ssh_cmd = ['ssh', '-p', str(port), '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', clean_server, f'mkdir -p {remote_dir}']
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[red]Failed to create remote directory: {result.stderr}[/red]")
            return False
        
        # Files to sync (essential configuration)
        files_to_sync = [
            'docker-compose-hub.yml',
            '.env.docker',
            'config.yml.local',
            'swarm_config.env',
            '.nginx-custom.conf.tpl',
            '.nginx-custom-entrypoint.sh',
        ]
        
        # Sync individual files
        for filename in files_to_sync:
            local_path = self.base_dir / filename
            if local_path.exists():
                rsync_cmd = [
                    'rsync', '-avz', '--progress',
                    '-e', ssh_opts,
                    str(local_path),
                    f'{clean_server}:{remote_dir}/'
                ]
                result = subprocess.run(rsync_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    console.print(f"[yellow]Warning: Failed to sync {filename}[/yellow]")
        
        # Sync setup_csv directory
        setup_csv_path = self.base_dir / 'setup_csv'
        if setup_csv_path.exists() and setup_csv_path.is_dir():
            console.print(f"[dim]Syncing setup_csv directory...[/dim]")
            # Ensure parent exists
            self._run_cmd(['ssh', '-p', str(port), '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', clean_server, f'mkdir -p {remote_dir}/setup_csv'], capture=True)
            rsync_cmd = [
                'rsync', '-avz', '--progress',
                '-e', ssh_opts,
                str(setup_csv_path) + '/',
                f'{clean_server}:{remote_dir}/setup_csv/'
            ]
            result = subprocess.run(rsync_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[yellow]Warning: Failed to sync setup_csv: {result.stderr}[/yellow]")
        
        # Sync dev_databases if exists
        dev_db_path = self.base_dir / 'data' / 'dev_databases'
        if dev_db_path.exists() and dev_db_path.is_dir():
            console.print(f"[dim]Syncing dev_databases directory...[/dim]")
            # Ensure parent exists
            self._run_cmd(['ssh', '-p', str(port), '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', clean_server, f'mkdir -p {remote_dir}/data/dev_databases'], capture=True)
            rsync_cmd = [
                'rsync', '-avz', '--progress',
                '-e', ssh_opts,
                str(dev_db_path) + '/',
                f'{clean_server}:{remote_dir}/data/dev_databases/'
            ]
            result = subprocess.run(rsync_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[yellow]Warning: Failed to sync dev_databases: {result.stderr}[/yellow]")
        
        console.print(f"[green]✓ Files synced to remote server[/green]")
        return True

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
        
        This sets up the SSH tunnel for the Docker socket.
        """
        if not server:
            return True
            
        # Start the tunnel. This handles authentication.
        socket_path = self._start_ssh_tunnel(server)
        if not socket_path:
            return False
            
        # Verify Docker access through the tunnel
        result = self._run_cmd(['docker', 'version', '--format', '{{.Server.Version}}'], server=server, capture=True)
        if result.returncode == 0:
            console.print(f"[green]✓ Connected to Docker on {server} (v{result.stdout.strip()})[/green]")
            return True
        else:
            console.print(f"[red]Failed to verify Docker access on {server}[/red]")
            self._stop_ssh_tunnel()
            return False

    def _docker_login(self, server: Optional[str] = None) -> bool:
        """Perform docker login if configured and not using Docker Hub.
        
        Args:
            server: Optional SSH URL for remote execution
            
        Returns:
            True if login succeeded or was skipped (not required), False on failure.
        """
        docker_cfg = self.config_mgr.get('docker', {})
        registry = docker_cfg.get('image_registry', 'tylconsulting')
        
        # Determine if it's Docker Hub
        # Logic matches push.sh: "docker.io" or simple names (no dot, no colon, not localhost)
        is_docker_hub = "docker.io" in registry or ('.' not in registry and ':' not in registry and registry != 'localhost')
        
        if is_docker_hub:
            return True
        
        # Check for credentials
        username = docker_cfg.get('registry_username')
        password = docker_cfg.get('registry_password')
        
        if not username or not password:
            # Custom registry but no credentials - assume public or already logged in?
            # User requirement says "login active only when pull is not from docker hub"
            # If they didn't provide credentials, we can't login.
            console.print(f"[dim]Custom registry '{registry}' detected but no credentials in config. Skipping login.[/dim]")
            return True
            
        console.print(f"[dim]Logging in to registry {registry}...[/dim]")
        
        # Use simple 'docker login' with password via stdin
        # This prevents the password from showing up in process lists
        cmd = ['docker', 'login', registry, '-u', username, '--password-stdin']
        
        try:
            # We need to manually handle stdin for subprocess
            # docker login reads from stdin
            
            # Security Note: This passes password in memory.
            # Avoid printing cmd (it doesn't have password, but good practice)
            
            # Reuse _run_cmd logic? _run_cmd handles remote context/ssh wrapping.
            # But passing stdin to _run_cmd isn't currently supported directly in the wrapper signature
            # (it takes env, not input).
            
            # We'll implement a specific login run logic reusing basic principles
            
            import subprocess
            input_bytes = f"{password}\n".encode('utf-8')
            
            # Start process
            if server:
                 # Check if we are using Docker Context (preferred)
                 if self._active_docker_context:
                     # Just run local docker command which points to remote context
                     result = subprocess.run(
                        cmd, 
                        input=input_bytes, 
                        capture_output=True, 
                        text=False  # We use bytes input/output
                     )
                 elif self._tunnel_socket:
                     # Use DOCKER_HOST
                     env = os.environ.copy()
                     env['DOCKER_HOST'] = f"unix://{self._tunnel_socket}"
                     result = subprocess.run(
                        cmd,
                        input=input_bytes,
                        capture_output=True,
                        env=env,
                        text=False
                     )
                 else:
                     # SSH wrapper (last resort or specific cases)
                     # Handling stdin via SSH wrapper requires care
                     # We can pipe: echo password | ssh host docker login ...
                     clean_server = server.replace('ssh://', '')
                     
                     # We must construct a safe command string
                     # Using docker login --password-stdin on remote 
                     remote_cmd = f"docker login {registry} -u {username} --password-stdin"
                     
                     ssh_cmd = [
                        'ssh',
                        '-o', 'BatchMode=yes',
                        '-o', 'StrictHostKeyChecking=no',
                        clean_server,
                        remote_cmd
                     ]
                     
                     result = subprocess.run(
                        ssh_cmd,
                        input=input_bytes,
                        capture_output=True,
                        text=False
                     )
            else:
                 # Local
                 result = subprocess.run(
                    cmd,
                    input=input_bytes,
                    capture_output=True,
                    text=False
                 )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Logged in to {registry}[/green]")
                return True
            else:
                try:
                    err = result.stderr.decode('utf-8').strip()
                except:
                    err = str(result.stderr)
                console.print(f"[red]Login failed: {err}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]Error during docker login: {e}[/red]")
            return False


    def up(self, server: Optional[str] = None) -> bool:
        """Pull images and start containers."""
        previous_context = None
        use_docker_context = False
        
        try:
            # For remote deployment, try Docker Context first (preferred)
            if server:
                console.print("[dim]Attempting Docker Context connection...[/dim]")
                success, previous_context = self._use_docker_context(server)
                if success:
                    use_docker_context = True
                    console.print("[green]✓ Using Docker Context for remote deployment[/green]")
                else:
                    console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                    # Fallback to SSH Tunnel (existing approach)
                    if not self.check_connection(server):
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
            
            # Perform docker login if needed
            if not self._docker_login(server=server):
                return False
                
            # Validate configuration
            console.print("[dim]Validating configuration...[/dim]")
            if not self.config_mgr.validate():
                return False
            
            # Generate .env.docker with correct SERVER_NAME
            if not self._ensure_env_docker(remote_hostname=remote_hostname):
                return False
                
            # Nginx and custom config support
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

            # Prepare for deployment
            compose_file_to_use = '.docker-compose.server.yml' if use_custom_compose else self.compose_file
            
            # If deploying to remote server, we MUST ensure images are pullable and mounts are remapped
            if server:
                 remote_base_dir = "/tmp/thothai_deploy"
                 remote_dest_conn = server.replace('ssh://', '')
                 
                 console.print(f"[dim]Preparing remote deployment on {remote_dest_conn}...[/dim]")
                 
                 # 1. Create and clean remote directory
                 self._run_cmd(['rm', '-rf', remote_base_dir], server=server, capture=True)
                 self._run_cmd(['mkdir', '-p', remote_base_dir], server=server, capture=True)
                 
                 # 2. Files to copy (essential configuration + any mounted local file)
                 # We will identify these during the remapping pass.
                 synced_files = set()
                 
                 # 3. Modify compose file locally to be remote-compatible
                 try:
                     import yaml
                     local_compose_path = self.base_dir / compose_file_to_use
                     if not local_compose_path.exists():
                         # Fallback to default if custom missing
                         local_compose_path = self.base_dir / self.compose_file
                     
                     with open(local_compose_path) as f:
                         data = yaml.safe_load(f)
                     
                     # Registry prefix for local-looking images
                     registry = self.config_mgr.get('docker', {}).get('image_registry', 'tylconsulting')
                     
                     # Process services
                     for service_name, service_config in data.get('services', {}).items():
                         # a. Correct image names (e.g. thoth-backend -> tylconsulting/thoth-backend)
                         image = service_config.get('image', '')
                         if image and (not '/' in image or image.startswith('thoth-')):
                             if not '/' in image:
                                # Avoid prefixing already prefixed images if they happen to start with thoth-
                                service_config['image'] = f"{registry}/{image}"
                         
                         # b. Strip build sections (we only pull on remote)
                         if 'build' in service_config:
                             del service_config['build']
                         
                         # c. Remap volume mounts
                         if 'volumes' in service_config:
                             new_volumes = []
                             for vol in service_config.get('volumes', []):
                                 if isinstance(vol, str):
                                     parts = vol.split(':')
                                     if len(parts) >= 2:
                                         src = parts[0]
                                         if src.startswith('./'):
                                             local_path = self.base_dir / src
                                             if local_path.is_file() and local_path.exists():
                                                 # Map to remote base dir and sync
                                                 filename = local_path.name
                                                 if filename not in synced_files:
                                                     self._copy_file(str(local_path), f"{remote_base_dir}/{filename}", server=server)
                                                     synced_files.add(filename)
                                                 
                                                 parts[0] = f"{remote_base_dir}/{filename}"
                                                 new_volumes.append(':'.join(parts))
                                                 continue
                                             elif local_path.is_dir():
                                                 # Skip directories for now (production environment usually doesn't need dev source code)
                                                 # skipping the mount prevents "not a directory" errors if destination is a file in image.
                                                 continue
                                 new_volumes.append(vol)
                             service_config['volumes'] = new_volumes
                     
                     # Ensure essential config files are synced even if not explicitly in mounts
                     essential_files = ['.env.docker', 'config.yml.local', '.nginx-custom.conf.tpl', '.nginx-custom-entrypoint.sh']
                     for essential in essential_files:
                         if essential not in synced_files:
                             local_path = self.base_dir / essential
                             if local_path.exists():
                                 self._copy_file(str(local_path), f"{remote_base_dir}/{essential}", server=server)
                                 synced_files.add(essential)

                     # Save as temporary remote-ready compose file
                     compose_file_to_use = '.docker-compose.remote-deploy.yml'
                     with open(self.base_dir / compose_file_to_use, 'w') as f:
                         yaml.dump(data, f, default_flow_style=False)
                         
                 except Exception as e:
                     console.print(f"[yellow]Warning: Failed to prepare remote-ready compose file: {e}[/yellow]")
                     # We continue with original, but it will likely fail on mounts or images

            # Create network and volumes (on target)
            if not self._create_network(server=server):
                return False
            if not self._create_volumes(server=server):
                return False
            
            # Pull images using the (possibly remapped) compose file
            console.print("\n[bold]Pulling images...[/bold]")
            result = self._run_cmd(
                ['docker', 'compose', '-f', str(self.base_dir / compose_file_to_use), 'pull'],
                server=server
            )
            
            # Pull failure is often fatal for remote deployment
            if result.returncode != 0:
                console.print("[red]Failed to pull images[/red]")
                return False
            
            # Start containers
            console.print("\n[bold]Starting containers...[/bold]")
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
                
            return True
            
        finally:
            # Always restore Docker Context if we used it
            if previous_context and use_docker_context:
                self._restore_docker_context(previous_context)
    
    def down(self, server: Optional[str] = None) -> bool:
        """Stop and remove containers."""
        previous_context = None
        use_docker_context = False
        
        try:
            # For remote execution, try Docker Context first (preferred)
            if server:
                console.print("[dim]Attempting Docker Context connection for down...[/dim]")
                success, previous_context = self._use_docker_context(server)
                if success:
                    use_docker_context = True
                    console.print("[green]✓ Using Docker Context for remote down[/green]")
                else:
                    console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                    # Fallback to SSH Tunnel
                    if not self.check_connection(server):
                        return False

            mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
            if mode == 'swarm':
                return self.swarm_down(server=server)

            result = self._run_cmd(
                ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'down'],
                server=server
            )
            
            return result.returncode == 0
            
        finally:
            # Always restore Docker Context if we used it
            if previous_context and use_docker_context:
                self._restore_docker_context(previous_context)
    
    def status(self, server: Optional[str] = None) -> None:
        """Show container status."""
        previous_context = None
        use_docker_context = False
        
        try:
            # For remote execution, try Docker Context first (preferred)
            if server:
                console.print("[dim]Attempting Docker Context connection for status...[/dim]")
                success, previous_context = self._use_docker_context(server)
                if success:
                    use_docker_context = True
                    console.print("[green]✓ Using Docker Context for remote status[/green]")
                else:
                    console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                    # Fallback to SSH Tunnel
                    if not self.check_connection(server):
                        return

            mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
            if mode == 'swarm':
                self.swarm_status(server=server)
                return 

            self._run_cmd(
                ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'ps'],
                server=server
            )
            
        finally:
            # Always restore Docker Context if we used it
            if previous_context and use_docker_context:
                self._restore_docker_context(previous_context)
    
    def logs(self, service: Optional[str] = None, tail: int = 50, follow: bool = False, server: Optional[str] = None) -> None:
        """View container logs."""
        previous_context = None
        use_docker_context = False
        
        try:
            # For remote execution, try Docker Context first (preferred)
            if server:
                console.print("[dim]Attempting Docker Context connection for logs...[/dim]")
                success, previous_context = self._use_docker_context(server)
                if success:
                    use_docker_context = True
                    console.print("[green]✓ Using Docker Context for remote logs[/green]")
                else:
                    console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                    # Fallback to SSH Tunnel
                    if not self.check_connection(server):
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
            
        finally:
            # Always restore Docker Context if we used it
            if previous_context and use_docker_context:
                self._restore_docker_context(previous_context)
    
    def ps(self, server: Optional[str] = None, show_all: bool = False) -> None:
        """Show active services with detailed container/task information.
        
        Args:
            server: Optional SSH URL for remote execution
            show_all: If True, show all containers including stopped ones
        """
        previous_context = None
        use_docker_context = False
        
        try:
            # For remote execution, try Docker Context first (preferred)
            if server:
                console.print("[dim]Attempting Docker Context connection for ps...[/dim]")
                success, previous_context = self._use_docker_context(server)
                if success:
                    use_docker_context = True
                    console.print("[green]✓ Using Docker Context for remote ps[/green]")
                else:
                    console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                    # Fallback to SSH Tunnel
                    if not self.check_connection(server):
                        return

            mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
            if mode == 'swarm':
                self.swarm_ps(server=server)
                return 

            # Build docker compose ps command with enhanced formatting
            cmd = ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'ps', '--format', 'table']
            
            if show_all:
                cmd.append('-a')
            
            self._run_cmd(cmd, server=server)
            
        finally:
            # Always restore Docker Context if we used it
            if previous_context and use_docker_context:
                self._restore_docker_context(previous_context)
    
    def swarm_ps(self, service: Optional[str] = None, server: Optional[str] = None) -> None:
        """Show Swarm stack tasks with replica distribution.
        
        Args:
            service: Optional specific service name to show tasks for
            server: Optional SSH URL for remote execution
        """
        previous_context = None
        use_docker_context = False
        
        try:
            # For remote execution, try Docker Context first (preferred)
            if server:
                console.print("[dim]Attempting Docker Context connection for swarm ps...[/dim]")
                success, previous_context = self._use_docker_context(server)
                if success:
                    use_docker_context = True
                    console.print("[green]✓ Using Docker Context for remote swarm ps[/green]")
                else:
                    console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                    # Fallback to SSH Tunnel
                    if not self.check_connection(server):
                        return

            swarm_env = self._get_swarm_env()
            stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
            
            if service:
                # Show tasks for a specific service
                full_service_name = f"{stack_name}_{service}"
                console.print(f"\n[bold]Tasks for service: {full_service_name}[/bold]\n")
                self._run_cmd(['docker', 'service', 'ps', full_service_name], server=server)
            else:
                # Show all stack tasks
                console.print(f"\n[bold]Stack: {stack_name}[/bold]\n")
                self._run_cmd(['docker', 'stack', 'ps', stack_name], server=server)
            
        finally:
            # Always restore Docker Context if we used it
            if previous_context and use_docker_context:
                self._restore_docker_context(previous_context)

    def update(self, server: Optional[str] = None) -> bool:
        """Update containers to latest images."""
        previous_context = None
        use_docker_context = False
        
        try:
            # For remote execution, try Docker Context first (preferred)
            if server:
                console.print("[dim]Attempting Docker Context connection for update...[/dim]")
                success, previous_context = self._use_docker_context(server)
                if success:
                    use_docker_context = True
                    console.print("[green]✓ Using Docker Context for remote update[/green]")
                else:
                    console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                    # Fallback to SSH Tunnel
                    if not self.check_connection(server):
                        return False

            mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
            if mode == 'swarm':
                return self.swarm_update(server=server)

            # Perform docker login if needed
            if not self._docker_login(server=server):
                return False

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
            
        finally:
            # Always restore Docker Context if we used it
            if previous_context and use_docker_context:
                self._restore_docker_context(previous_context)
    
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

        if server and cmd[0] == 'docker' and self._tunnel_socket:
            # Use the established tunnel for Docker commands
            full_env['DOCKER_HOST'] = f"unix://{self._tunnel_socket}"
            
            # Run locally targeting the tunneled socket
            return subprocess.run(cmd, cwd=self.base_dir, capture_output=capture, text=True, env=full_env)
            
        elif server and cmd[0] == 'docker':
            # Fallback if tunnel is not active (should not happen if check_connection was called)
            docker_host = server
            if not docker_host.startswith('ssh://'):
                 docker_host = f"ssh://{docker_host}"
            
            full_env['DOCKER_HOST'] = docker_host
            return subprocess.run(cmd, cwd=self.base_dir, capture_output=capture, text=True, env=full_env)
            
        elif server:
            # Clean connection string for standard ssh command
            clean_server = server.replace('ssh://', '')
            
            # Determine a safe ControlPath (mirroring _start_ssh_tunnel)
            ssh_dir = Path.home() / '.ssh'
            if ssh_dir.exists() and os.access(ssh_dir, os.W_OK):
                control_path = '~/.ssh/thothai-%C'
            else:
                control_path = f'/tmp/thothai-{hashlib.md5(clean_server.encode()).hexdigest()[:8]}-%C'

            # For non-docker commands (e.g. strict shell commands), use SSH wrapper
            ssh_cmd = [
                'ssh',
                '-o', 'ControlMaster=auto',
                '-o', 'ControlPath=' + control_path,
                '-o', 'ControlPersist=600',
                clean_server,
                ' '.join(cmd)
            ]
            return subprocess.run(ssh_cmd, cwd=self.base_dir, capture_output=capture, text=True)
        else:
            return subprocess.run(cmd, cwd=self.base_dir, capture_output=capture, text=True, env=full_env)

    def _copy_file(self, local_path: str, remote_path: str, server: str) -> bool:
        """Copy a file to a remote server using scp with the same tunnel as _run_cmd."""
        clean_server = server.replace('ssh://', '')
        
        # Determine a safe ControlPath (mirroring _start_ssh_tunnel)
        ssh_dir = Path.home() / '.ssh'
        if ssh_dir.exists() and os.access(ssh_dir, os.W_OK):
            control_path = '~/.ssh/thothai-%C'
        else:
            control_path = f'/tmp/thothai-{hashlib.md5(clean_server.encode()).hexdigest()[:8]}-%C'

        scp_cmd = [
            'scp',
            '-o', 'ControlMaster=auto',
            '-o', 'ControlPath=' + control_path,
            '-o', 'BatchMode=yes',
            local_path,
            f"{clean_server}:{remote_path}"
        ]
        
        result = subprocess.run(scp_cmd, capture_output=True)
        return result.returncode == 0

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
        previous_context = None
        use_docker_context = False
        
        try:
            # For remote deployment, try Docker Context first (preferred)
            if server:
                console.print("[dim]Attempting Docker Context connection for Swarm...[/dim]")
                success, previous_context = self._use_docker_context(server)
                if success:
                    use_docker_context = True
                    console.print("[green]✓ Using Docker Context for Swarm deployment[/green]")
                else:
                    console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                    # Fallback to SSH Tunnel
                    if not self.check_connection(server):
                        return False
            
            # Extract remote hostname for remote deployments
            remote_hostname = None
            if server:
                remote_hostname = self._extract_hostname_from_server(server)
                self._remote_hostname = remote_hostname
                console.print(f"[dim]Deploying Swarm to remote server: {remote_hostname}[/dim]")
                
                # Sync files to remote server (Required for bind-mounts like setup_csv)
                if not self._rsync_files(server):
                     console.print("[yellow]Warning: File sync failed, deployment might miss data[/yellow]")
            
            # Perform docker login if needed
            if not self._docker_login(server=server):
                return False
            
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
                
                # Dynamic adjustment for secrets/configs namespacing
                # We want to map the short names in YAML to the namespaced versions created by _manage_swarm_resources
                # e.g. "external: true" -> "external:\n      name: ${STACK_NAME}_thoth_env_config"
                stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
                
                replacements = {
                    'thoth_env_config': f'{stack_name}_thoth_env_config',
                    'thoth_config_yml': f'{stack_name}_thoth_config_yml',
                    'thoth_env_docker': f'{stack_name}_thoth_env_docker',
                }
                
                import yaml
                stack_data = yaml.safe_load(processed_content)
                
                # Fix Secrets
                if 'secrets' in stack_data:
                    for secret_key, secret_def in stack_data['secrets'].items():
                        if secret_key in replacements and secret_def.get('external'):
                            secret_def['external'] = {'name': replacements[secret_key]}
                
                # Fix Configs
                if 'configs' in stack_data:
                    for config_key, config_def in stack_data['configs'].items():
                        if config_key in replacements and config_def.get('external'):
                            config_def['external'] = {'name': replacements[config_key]}
                            
                processed_content = yaml.dump(stack_data, default_flow_style=False)
                
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

                # Inject placement constraints for remote deployment (Pin to manager for persistence/bind-mounts)
                if server:
                    try:
                        import yaml
                        stack_data = yaml.safe_load(processed_content)
                        if 'services' in stack_data:
                            for service_name, service_def in stack_data['services'].items():
                                if 'deploy' not in service_def:
                                    service_def['deploy'] = {}
                                if 'placement' not in service_def['deploy']:
                                    service_def['deploy']['placement'] = {}
                                if 'constraints' not in service_def['deploy']['placement']:
                                    service_def['deploy']['placement']['constraints'] = []
                                
                                # Add pinning constraint
                                constraints = service_def['deploy']['placement']['constraints']
                                if not any('node.role == manager' in str(c) for c in constraints):
                                    constraints.append('node.role == manager')
                            
                            processed_content = yaml.dump(stack_data, default_flow_style=False)
                            console.print("[dim]Injected placement constraints: node.role == manager[/dim]")
                    except ImportError:
                        console.print("[yellow]Warning: PyYAML not installed, skipping constraint injection[/yellow]")
                    except Exception as e:
                         console.print(f"[yellow]Warning: Failed to inject constraints: {e}[/yellow]")
                
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
                    
        finally:
            # Always restore Docker Context if we used it
            if previous_context and use_docker_context:
                self._restore_docker_context(previous_context)
    
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
        
        # Use remote hostname if set, then configured server_name, finally localhost
        host = self._remote_hostname or self.config_mgr.get('server_name') or 'localhost'
        
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

    def prune(self, server: Optional[str] = None, remove_volumes: bool = True, remove_images: bool = True) -> bool:
        """Remove all Docker Compose artifacts for ThothAI.
        
        Args:
            server: Optional SSH URL for remote execution
            remove_volumes: Whether to remove Docker volumes
            remove_images: Whether to remove Docker images
            
        Returns:
            True if cleanup was successful
        """
        previous_context = None
        use_docker_context = False
        
        try:
            # For remote execution, try Docker Context first (preferred)
            if server:
                console.print("[dim]Attempting Docker Context connection for prune...[/dim]")
                success, previous_context = self._use_docker_context(server)
                if success:
                    use_docker_context = True
                    console.print("[green]✓ Using Docker Context for remote prune[/green]")
                else:
                    console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                    # Fallback to SSH Tunnel
                    if not self.check_connection(server):
                        return False
            
            success = True
            
            # 1. Stop and remove containers via docker compose
            console.print("[dim]Stopping and removing containers...[/dim]")
            result = self._run_cmd(
                ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'down', '--remove-orphans'],
                server=server,
                capture=True
            )
            if result.returncode == 0:
                console.print("[green]✓ Containers stopped and removed[/green]")
            else:
                console.print("[yellow]⚠ Some containers may not have been removed[/yellow]")
            
            # 2. Remove any remaining thoth containers
            console.print("[dim]Checking for remaining containers...[/dim]")
            result = self._run_cmd(
                ['docker', 'ps', '-a', '--filter', 'name=thoth', '--format', '{{.ID}}'],
                server=server,
                capture=True
            )
            if result.returncode == 0 and result.stdout.strip():
                container_ids = result.stdout.strip().split('\n')
                for cid in container_ids:
                    if cid:
                        self._run_cmd(['docker', 'rm', '-f', cid], server=server, capture=True)
                console.print(f"[green]✓ Removed {len(container_ids)} remaining container(s)[/green]")
            
            # 3. Remove network
            console.print("[dim]Removing network...[/dim]")
            result = self._run_cmd(
                ['docker', 'network', 'rm', 'thoth-network'],
                server=server,
                capture=True
            )
            if result.returncode == 0:
                console.print("[green]✓ Network removed[/green]")
            else:
                console.print("[dim]Network already removed or not found[/dim]")
            
            # 4. Remove volumes if requested
            if remove_volumes:
                console.print("[dim]Removing volumes...[/dim]")
                volumes = [
                    'thoth-secrets',
                    'thoth-backend-db',
                    'thoth-backend-static',
                    'thoth-backend-media',
                    'thoth-backend-secrets',
                    'thoth-logs',
                    'thoth-frontend-cache',
                    'thoth-qdrant-data',
                    'thoth-shared-data',
                    'thoth-data-exchange'
                ]
                removed_count = 0
                for vol in volumes:
                    result = self._run_cmd(
                        ['docker', 'volume', 'rm', vol],
                        server=server,
                        capture=True
                    )
                    if result.returncode == 0:
                        removed_count += 1
                console.print(f"[green]✓ Removed {removed_count} volume(s)[/green]")
            
            # 5. Remove images if requested
            if remove_images:
                console.print("[dim]Removing images...[/dim]")
                result = self._run_cmd(
                    ['docker', 'images', '--filter', 'reference=thothai/*', '--format', '{{.ID}}'],
                    server=server,
                    capture=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    image_ids = list(set(result.stdout.strip().split('\n')))  # Deduplicate
                    for img_id in image_ids:
                        if img_id:
                            self._run_cmd(['docker', 'rmi', '-f', img_id], server=server, capture=True)
                    console.print(f"[green]✓ Removed {len(image_ids)} image(s)[/green]")
                else:
                    console.print("[dim]No ThothAI images found[/dim]")
            
            # 6. Remove generated local files (only if local, not remote)
            if not server:
                console.print("[dim]Removing generated configuration files...[/dim]")
                generated_files = [
                    '.docker-compose.server.yml',
                    '.docker-compose.server.remote.yml',
                    '.nginx-custom.conf.tpl',
                    '.nginx-custom-entrypoint.sh',
                    'docker-stack.gen.yml'
                ]
                removed_count = 0
                for filename in generated_files:
                    filepath = self.base_dir / filename
                    if filepath.exists():
                        filepath.unlink()
                        removed_count += 1
                if removed_count > 0:
                    console.print(f"[green]✓ Removed {removed_count} generated file(s)[/green]")
            
            return success
            
        finally:
            # Always restore Docker Context if we used it
            if previous_context and use_docker_context:
                self._restore_docker_context(previous_context)

    def swarm_prune(self, server: Optional[str] = None, remove_volumes: bool = True, remove_images: bool = True) -> bool:
        """Remove all Docker Swarm artifacts for ThothAI.
        
        Args:
            server: Optional SSH URL for remote execution
            remove_volumes: Whether to remove Docker volumes
            remove_images: Whether to remove Docker images
            
        Returns:
            True if cleanup was successful
        """
        previous_context = None
        use_docker_context = False
        
        try:
            # For remote execution, try Docker Context first (preferred)
            if server:
                console.print("[dim]Attempting Docker Context connection for Swarm prune...[/dim]")
                success, previous_context = self._use_docker_context(server)
                if success:
                    use_docker_context = True
                    console.print("[green]✓ Using Docker Context for remote Swarm prune[/green]")
                else:
                    console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                    # Fallback to SSH Tunnel
                    if not self.check_connection(server):
                        return False
            
            success = True
            swarm_env = self._get_swarm_env()
            stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
            
            # 1. Remove stack
            console.print(f"[dim]Removing stack '{stack_name}'...[/dim]")
            result = self._run_cmd(
                ['docker', 'stack', 'rm', stack_name],
                server=server,
                capture=True
            )
            if result.returncode == 0:
                console.print(f"[green]✓ Stack '{stack_name}' removed[/green]")
            else:
                console.print(f"[yellow]⚠ Stack may not exist or could not be removed[/yellow]")
            
            # 2. Wait for services to be removed
            console.print("[dim]Waiting for services to be removed...[/dim]")
            import time
            max_wait = 60
            start_time = time.time()
            while time.time() - start_time < max_wait:
                result = self._run_cmd(
                    ['docker', 'service', 'ls', '--filter', f'label=com.docker.stack.namespace={stack_name}', '--format', '{{.Name}}'],
                    server=server,
                    capture=True
                )
                if result.returncode == 0 and not result.stdout.strip():
                    break
                time.sleep(2)
            console.print("[green]✓ Services removed[/green]")
            
            # 3. Remove secrets
            console.print("[dim]Removing secrets...[/dim]")
            secrets_to_remove = [
                f"{stack_name}_thoth_env_config",
                f"{stack_name}_thoth_config_yml"
            ]
            for secret in secrets_to_remove:
                self._run_cmd(['docker', 'secret', 'rm', secret], server=server, capture=True)
            console.print("[green]✓ Secrets removed[/green]")
            
            # 4. Remove configs
            console.print("[dim]Removing configs...[/dim]")
            configs_to_remove = [
                f"{stack_name}_thoth_env_docker"
            ]
            for config in configs_to_remove:
                self._run_cmd(['docker', 'config', 'rm', config], server=server, capture=True)
            console.print("[green]✓ Configs removed[/green]")
            
            # 5. Remove network (swarm overlay)
            console.print("[dim]Removing network...[/dim]")
            result = self._run_cmd(
                ['docker', 'network', 'rm', f'{stack_name}_thoth-network'],
                server=server,
                capture=True
            )
            # Also try without stack prefix
            self._run_cmd(['docker', 'network', 'rm', 'thoth-network'], server=server, capture=True)
            console.print("[green]✓ Network removed[/green]")
            
            # 6. Remove volumes if requested
            if remove_volumes:
                console.print("[dim]Removing volumes...[/dim]")
                volumes = [
                    'thoth-secrets',
                    'thoth-backend-db',
                    'thoth-backend-static',
                    'thoth-backend-media',
                    'thoth-backend-secrets',
                    'thoth-logs',
                    'thoth-frontend-cache',
                    'thoth-qdrant-data',
                    'thoth-shared-data',
                    'thoth-data-exchange'
                ]
                removed_count = 0
                for vol in volumes:
                    result = self._run_cmd(
                        ['docker', 'volume', 'rm', vol],
                        server=server,
                        capture=True
                    )
                    if result.returncode == 0:
                        removed_count += 1
                console.print(f"[green]✓ Removed {removed_count} volume(s)[/green]")
            
            # 7. Remove images if requested
            if remove_images:
                console.print("[dim]Removing images...[/dim]")
                result = self._run_cmd(
                    ['docker', 'images', '--filter', 'reference=thothai/*', '--format', '{{.ID}}'],
                    server=server,
                    capture=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    image_ids = list(set(result.stdout.strip().split('\n')))
                    for img_id in image_ids:
                        if img_id:
                            self._run_cmd(['docker', 'rmi', '-f', img_id], server=server, capture=True)
                    console.print(f"[green]✓ Removed {len(image_ids)} image(s)[/green]")
                else:
                    console.print("[dim]No ThothAI images found[/dim]")
            
            # 8. Remove generated local files (only if local)
            if not server:
                console.print("[dim]Removing generated configuration files...[/dim]")
                generated_files = [
                    '.docker-compose.server.yml',
                    '.docker-compose.server.remote.yml',
                    '.nginx-custom.conf.tpl',
                    '.nginx-custom-entrypoint.sh',
                    'docker-stack.gen.yml'
                ]
                removed_count = 0
                for filename in generated_files:
                    filepath = self.base_dir / filename
                    if filepath.exists():
                        filepath.unlink()
                        removed_count += 1
                if removed_count > 0:
                    console.print(f"[green]✓ Removed {removed_count} generated file(s)[/green]")
            
            return success
            
        finally:
            # Always restore Docker Context if we used it
            if previous_context and use_docker_context:
                self._restore_docker_context(previous_context)

