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
    
    def _create_volumes(self) -> bool:
        """Create required Docker volumes."""
        volumes = [
            'thoth-secrets',
            'thoth-backend-static',
            'thoth-backend-media',
            'thoth-frontend-cache',
            'thoth-qdrant-data',
            'thoth-shared-data'
        ]
        
        console.print("[dim]Checking Docker volumes...[/dim]")
        
        for volume_name in volumes:
            result = subprocess.run(
                ['docker', 'volume', 'ls', '--format', '{{.Name}}'],
                capture_output=True,
                text=True
            )
            
            if volume_name not in result.stdout.split('\n'):
                result = subprocess.run(
                    ['docker', 'volume', 'create', volume_name],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    console.print(f"[red]Failed to create volume '{volume_name}'[/red]")
                    return False
        
        return True
    
    def _create_network(self) -> bool:
        """Create Docker network if it doesn't exist."""
        network_name = 'thoth-network'
        
        result = subprocess.run(
            ['docker', 'network', 'ls', '--format', '{{.Name}}'],
            capture_output=True,
            text=True
        )
        
        if network_name not in result.stdout.split('\n'):
            console.print(f"[dim]Creating network '{network_name}'...[/dim]")
            result = subprocess.run(
                ['docker', 'network', 'create', network_name],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                console.print(f"[red]Failed to create network[/red]")
                return False
        
        return True
    
    def up(self) -> bool:
        """Pull images and start containers."""
        mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        if mode == 'swarm':
            return self.swarm_up()
            
        # Validate configuration
        console.print("[dim]Validating configuration...[/dim]")
        if not self.config_mgr.validate():
            return False
        
        # Generate .env.docker
        if not self._ensure_env_docker():
            return False
        
        # Create network and volumes
        if not self._create_network():
            return False
        if not self._create_volumes():
            return False
        
        # Pull images
        console.print("\n[bold]Pulling images from Docker Hub...[/bold]")
        result = subprocess.run(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'pull'],
            cwd=self.base_dir
        )
        
        if result.returncode != 0:
            console.print("[red]Failed to pull images[/red]")
            return False
        
        # Start containers
        console.print("\n[bold]Starting containers...[/bold]")
        result = subprocess.run(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'up', '-d'],
            cwd=self.base_dir
        )
        
        if result.returncode != 0:
            console.print("[red]Failed to start containers[/red]")
            return False
        
        return True
    
    def down(self) -> bool:
        """Stop and remove containers."""
        mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        if mode == 'swarm':
            return self.swarm_down()

        result = subprocess.run(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'down'],
            cwd=self.base_dir
        )
        
        return result.returncode == 0
    
    def status(self) -> None:
        """Show container status."""
        mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        if mode == 'swarm':
            self.swarm_status()
            return

        subprocess.run(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'ps'],
            cwd=self.base_dir
        )
    
    def logs(self, service: Optional[str] = None, tail: int = 50, follow: bool = False) -> None:
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
            subprocess.run(cmd, cwd=self.base_dir)
            return

        cmd = ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'logs']
        
        if follow:
            cmd.append('-f')
        else:
            cmd.extend(['--tail', str(tail)])
        
        if service:
            cmd.append(service)
        
        subprocess.run(cmd, cwd=self.base_dir)
    
    def update(self) -> bool:
        """Update containers to latest images."""
        mode = self.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        if mode == 'swarm':
            return self.swarm_update()

        # Ensure configuration is up-to-date
        if not self._ensure_env_docker():
            return False
        
        # Pull latest images
        console.print("\n[bold]Pulling latest images...[/bold]")
        result = subprocess.run(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'pull'],
            cwd=self.base_dir
        )
        
        if result.returncode != 0:
            console.print("[red]Failed to pull latest images[/red]")
            return False
        
        # Recreate containers
        console.print("\n[bold]Recreating containers...[/bold]")
        result = subprocess.run(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'up', '-d', '--force-recreate'],
            cwd=self.base_dir
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
            
        # Network
        console.print(f"[dim]Ensuring overlay network '{stack_name}_thoth-network' exists...[/dim]")
        self._run_cmd(['docker', 'network', 'create', '--driver', 'overlay', '--attachable', f"{stack_name}_thoth-network"], server)
        
        return True

    def swarm_up(self, server: Optional[str] = None) -> bool:
        """Deploy ThothAI to Docker Swarm."""
        if not self.config_mgr.validate():
            return False
        
        if not self.config_mgr.generate_env_docker():
            return False
        
        if not self.config_mgr.generate_swarm_config():
            return False
            
        swarm_env = self._get_swarm_env()
        stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
        stack_file = self.config_mgr.get('docker', {}).get('stack_file', 'docker-stack.yml')
        
        if not (self.base_dir / stack_file).exists():
            console.print(f"[red]Error: Stack file '{stack_file}' not found[/red]")
            return False
            
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
            ['docker', 'stack', 'deploy', '-c', stack_file, stack_name],
            server=server,
            env=swarm_env
        )
        
        if result.returncode != 0:
            console.print("[red]Failed to deploy stack[/red]")
            return False
            
        return True

    def swarm_down(self, server: Optional[str] = None) -> bool:
        """Remove ThothAI from Docker Swarm."""
        swarm_env = self._get_swarm_env()
        stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
        
        console.print(f"\n[bold yellow]Removing stack '{stack_name}'...[/bold yellow]")
        result = self._run_cmd(['docker', 'stack', 'rm', stack_name], server)
        
        # Cleanup secrets/configs after a short delay
        import time
        time.sleep(2)
        self._run_cmd(['docker', 'secret', 'rm', f"{stack_name}_thoth_env_config", f"{stack_name}_thoth_config_yml"], server)
        self._run_cmd(['docker', 'config', 'rm', f"{stack_name}_thoth_env_docker"], server)
        
        return result.returncode == 0

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
