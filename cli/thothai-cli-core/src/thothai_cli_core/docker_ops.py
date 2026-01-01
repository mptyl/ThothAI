# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Docker operations for CSV and SQLite management."""

import subprocess
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from rich.console import Console

console = Console()


class DockerOperations:
    """Handle Docker operations for local and remote connections."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config
        self.connection = config.get('docker', {}).get('connection', 'local')
        self.mode = config.get('docker', {}).get('mode', 'swarm')
        self.stack_name = config.get('docker', {}).get('stack_name', 'thothai-swarm')
        self.service = config.get('docker', {}).get('service', 'backend')
        self.db_service = config.get('docker', {}).get('db_service', 'sql-generator')
        self.paths = config.get('paths', {
            'data_exchange': '/app/data_exchange',
            'shared_data': '/app/data'
        })
    
    def _run_command(self, cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Execute command locally or via SSH."""
        if self.connection == 'ssh':
            ssh_config = self.config.get('ssh', {})
            ssh_cmd = ['ssh', '-p', str(ssh_config.get('port', 22))]
            
            if ssh_config.get('key_file'):
                ssh_cmd.extend(['-i', ssh_config['key_file']])
            
            ssh_cmd.append(f"{ssh_config.get('user')}@{ssh_config.get('host')}")
            ssh_cmd.append(' '.join(cmd))
            cmd = ssh_cmd
        
        result = subprocess.run(cmd, capture_output=capture_output, text=True)
        return result
    
    def _get_container_name(self, service: str) -> Optional[str]:
        """Get container name for a service."""
        if self.mode == 'swarm':
            # Swarm: thothai-swarm_backend.1.xxx
            filter_name = f"{self.stack_name}_{service}"
        else:
            # Compose: thothai_backend_1 or thothai-backend-1
            filter_name = f"{self.stack_name}_{service}"
        
        cmd = ['docker', 'ps', '--filter', f'name={filter_name}', '--format', '{{.Names}}']
        result = self._run_command(cmd)
        
        if result.returncode != 0:
            console.print(f"[red]Error finding container: {result.stderr}[/red]")
            return None
        
        containers = result.stdout.strip().split('\n')
        if containers and containers[0]:
            return containers[0]
        
        console.print(f"[red]No container found for service: {service}[/red]")
        return None
    
    def test_connection(self) -> bool:
        """Test Docker connection."""
        console.print("[cyan]Testing Docker connection...[/cyan]")
        
        cmd = ['docker', 'ps']
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            console.print("[green]✓ Docker connection successful[/green]")
            
            # Try to find service containers
            backend = self._get_container_name(self.service)
            if backend:
                console.print(f"[green]✓ Found backend container: {backend}[/green]")
            
            db_service = self._get_container_name(self.db_service)
            if db_service:
                console.print(f"[green]✓ Found db service container: {db_service}[/green]")
            
            return True
        else:
            console.print(f"[red]✗ Docker connection failed: {result.stderr}[/red]")
            return False
    
    # === CSV Operations ===
    
    def csv_list(self):
        """List CSV files in data_exchange volume."""
        container = self._get_container_name(self.service)
        if not container:
            return
        
        cmd = ['docker', 'exec', container, 'ls', '-lh', self.paths['data_exchange']]
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            console.print(f"\n[bold]Files in {self.paths['data_exchange']}:[/bold]")
            console.print(result.stdout)
        else:
            console.print(f"[red]Error listing files: {result.stderr}[/red]")
    
    def csv_upload(self, file_path: str):
        """Upload CSV file to data_exchange volume."""
        local_path = Path(file_path)
        if not local_path.exists():
            console.print(f"[red]File not found: {file_path}[/red]")
            return
        
        container = self._get_container_name(self.service)
        if not container:
            return
        
        filename = local_path.name
        remote_path = f"{self.paths['data_exchange']}/{filename}"
        
        if self.connection == 'ssh':
            # SCP to remote, then docker cp
            ssh_config = self.config.get('ssh', {})
            host = f"{ssh_config.get('user')}@{ssh_config.get('host')}"
            
            # SCP to /tmp on remote
            scp_cmd = ['scp']
            if ssh_config.get('key_file'):
                scp_cmd.extend(['-i', ssh_config['key_file']])
            scp_cmd.extend(['-P', str(ssh_config.get('port', 22))])
            scp_cmd.extend([str(local_path), f"{host}:/tmp/{filename}"])
            
            result = subprocess.run(scp_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[red]SCP failed: {result.stderr}[/red]")
                return
            
            # Docker cp on remote
            cmd = ['docker', 'cp', f'/tmp/{filename}', f'{container}:{remote_path}']
        else:
            # Local docker cp
            cmd = ['docker', 'cp', str(local_path), f'{container}:{remote_path}']
        
        result = self._run_command(cmd)
        if result.returncode == 0:
            console.print(f"[green]✓ Uploaded: {filename}[/green]")
        else:
            console.print(f"[red]Upload failed: {result.stderr}[/red]")
    
    def csv_download(self, filename: str, output_dir: str = '.'):
        """Download CSV file from data_exchange volume."""
        container = self._get_container_name(self.service)
        if not container:
            return
        
        remote_path = f"{self.paths['data_exchange']}/{filename}"
        local_path = Path(output_dir) / filename
        
        if self.connection == 'ssh':
            # Docker cp to /tmp on remote, then SCP to local
            ssh_config = self.config.get('ssh', {})
            host = f"{ssh_config.get('user')}@{ssh_config.get('host')}"
            
            # Docker cp on remote
            cmd = ['docker', 'cp', f'{container}:{remote_path}', f'/tmp/{filename}']
            result = self._run_command(cmd)
            if result.returncode != 0:
                console.print(f"[red]Docker cp failed: {result.stderr}[/red]")
                return
            
            # SCP from remote
            scp_cmd = ['scp']
            if ssh_config.get('key_file'):
                scp_cmd.extend(['-i', ssh_config['key_file']])
            scp_cmd.extend(['-P', str(ssh_config.get('port', 22))])
            scp_cmd.extend([f"{host}:/tmp/{filename}", str(local_path)])
            
            result = subprocess.run(scp_cmd, capture_output=True, text=True)
        else:
            # Local docker cp
            cmd = ['docker', 'cp', f'{container}:{remote_path}', str(local_path)]
            result = self._run_command(cmd)
        
        if result.returncode == 0:
            console.print(f"[green]✓ Downloaded to: {local_path}[/green]")
        else:
            console.print(f"[red]Download failed: {result.stderr}[/red]")
    
    def csv_delete(self, filename: str):
        """Delete CSV file from data_exchange volume."""
        container = self._get_container_name(self.service)
        if not container:
            return
        
        remote_path = f"{self.paths['data_exchange']}/{filename}"
        cmd = ['docker', 'exec', container, 'rm', remote_path]
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            console.print(f"[green]✓ Deleted: {filename}[/green]")
        else:
            console.print(f"[red]Delete failed: {result.stderr}[/red]")
    
    # === Database Operations ===
    
    def db_list(self):
        """List SQLite databases in shared_data volume."""
        container = self._get_container_name(self.db_service)
        if not container:
            return
        
        cmd = ['docker', 'exec', container, 'ls', '-lh', self.paths['shared_data']]
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            console.print(f"\n[bold]Databases in {self.paths['shared_data']}:[/bold]")
            console.print(result.stdout)
        else:
            console.print(f"[red]Error listing databases: {result.stderr}[/red]")
    
    def db_insert(self, db_path: str):
        """Insert SQLite database into shared_data volume."""
        local_path = Path(db_path)
        if not local_path.exists():
            console.print(f"[red]Database file not found: {db_path}[/red]")
            return
        
        container = self._get_container_name(self.db_service)
        if not container:
            return
        
        db_name = local_path.stem
        db_dir = f"{self.paths['shared_data']}/{db_name}"
        remote_path = f"{db_dir}/{db_name}.sqlite"
        
        # Create directory
        cmd = ['docker', 'exec', container, 'mkdir', '-p', db_dir]
        result = self._run_command(cmd)
        if result.returncode != 0:
            console.print(f"[red]Failed to create directory: {result.stderr}[/red]")
            return
        
        # Copy database
        if self.connection == 'ssh':
            ssh_config = self.config.get('ssh', {})
            host = f"{ssh_config.get('user')}@{ssh_config.get('host')}"
            
            # SCP to remote
            scp_cmd = ['scp']
            if ssh_config.get('key_file'):
                scp_cmd.extend(['-i', ssh_config['key_file']])
            scp_cmd.extend(['-P', str(ssh_config.get('port', 22))])
            scp_cmd.extend([str(local_path), f"{host}:/tmp/{db_name}.sqlite"])
            
            result = subprocess.run(scp_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[red]SCP failed: {result.stderr}[/red]")
                return
            
            # Docker cp on remote
            cmd = ['docker', 'cp', f'/tmp/{db_name}.sqlite', f'{container}:{remote_path}']
        else:
            # Local docker cp
            cmd = ['docker', 'cp', str(local_path), f'{container}:{remote_path}']
        
        result = self._run_command(cmd)
        if result.returncode == 0:
            console.print(f"[green]✓ Database inserted: {db_name}[/green]")
            console.print(f"  Location: {remote_path}")
        else:
            console.print(f"[red]Insert failed: {result.stderr}[/red]")
    
    def db_remove(self, name: str):
        """Remove SQLite database from shared_data volume."""
        container = self._get_container_name(self.db_service)
        if not container:
            return
        
        db_dir = f"{self.paths['shared_data']}/{name}"
        cmd = ['docker', 'exec', container, 'rm', '-rf', db_dir]
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            console.print(f"[green]✓ Database removed: {name}[/green]")
        else:
            console.print(f"[red]Remove failed: {result.stderr}[/red]")
