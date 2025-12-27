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
        result = subprocess.run(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'down'],
            cwd=self.base_dir
        )
        
        return result.returncode == 0
    
    def status(self) -> None:
        """Show container status."""
        subprocess.run(
            ['docker', 'compose', '-f', str(self.base_dir / self.compose_file), 'ps'],
            cwd=self.base_dir
        )
    
    def logs(self, service: Optional[str] = None, tail: int = 50, follow: bool = False) -> None:
        """View container logs."""
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
    
    def print_access_info(self) -> None:
        """Print access information."""
        ports = self.config_mgr.get('ports', {})
        admin = self.config_mgr.get('admin', {})
        
        console.print("\n[bold]Access URLs:[/bold]")
        console.print(f"  Main App:   http://localhost:{ports.get('nginx', 8040)}")
        console.print(f"  Frontend:   http://localhost:{ports.get('frontend', 3040)}")
        console.print(f"  Admin:      http://localhost:{ports.get('nginx', 8040)}/admin")
        
        console.print("\n[bold]Login Credentials:[/bold]")
        console.print(f"  Username: {admin.get('username', 'admin')}")
        console.print(f"  Password: [as configured in config.yml.local]")
