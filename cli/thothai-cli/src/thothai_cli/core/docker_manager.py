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
    
    def _ensure_env_docker(self) -> bool:
        """Ensure .env.docker exists and is up-to-date."""
        env_path = self.base_dir / '.env.docker'
        
        # Always regenerate to ensure it's current
        console.print("[dim]Generating .env.docker...[/dim]")
        if not self.config_mgr.generate_env_docker():
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
    
    def up(self, server: Optional[str] = None) -> bool:
        """Pull images and start containers."""
        mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        if mode == 'swarm':
            return self.swarm_up(server=server)
            
        # Validate configuration
        console.print("[dim]Validating configuration...[/dim]")
        if not self.config_mgr.validate():
            return False
        
        # Generate .env.docker
        if not self._ensure_env_docker():
            return False
        
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
        result = self._run_cmd(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'up', '-d'],
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
        if server:
            ssh_cmd = ['ssh', server, ' '.join(cmd)]
            return subprocess.run(ssh_cmd, cwd=self.base_dir, capture_output=capture, text=True)
        else:
            full_env = None
            if env:
                import os
                full_env = os.environ.copy()
                full_env.update(env)
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
        if not self.config_mgr.validate():
            return False
        
        if not self.config_mgr.generate_env_docker():
            return False
        
        if not self.config_mgr.generate_env_docker():
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
        
        if not (self.base_dir / stack_file).exists():
            console.print(f"[red]Error: Stack file '{stack_file}' not found[/red]")
            return False
            
        # Preprocess stack file to handle variable substitution in keys (which Docker doesn't support)
        # This replaces ${VAR} and ${VAR:-default} with values from swarm_env
        try:
            stack_content = (self.base_dir / stack_file).read_text(encoding='utf-8')
            processed_content = self._replace_env_vars(stack_content, swarm_env)
            
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
        
        console.print("\n[bold]Access URLs:[/bold]")
        console.print(f"  Main App:   http://localhost:{web_port}")
        console.print(f"  Frontend:   http://localhost:{frontend_port}")
        console.print(f"  Admin:      http://localhost:{web_port}/admin")
        
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
