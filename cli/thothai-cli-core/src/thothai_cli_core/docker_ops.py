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
        """Get container name for a service using labels first, then name convention."""
        # 1. Try label-based filtering (More robust)
        if self.mode == 'swarm':
            # Swarm services have specific labels
            # Filter by stack name and service name
            cmd = [
                'docker', 'ps', 
                '--filter', f'label=com.docker.stack.namespace={self.stack_name}',
                '--filter', f'label=com.docker.swarm.service.name={self.stack_name}_{service}',
                '--format', '{{.Names}}'
            ]
        else:
            # Compose services
            cmd = [
                'docker', 'ps', 
                '--filter', f'label=com.docker.compose.project={self.stack_name}',
                '--filter', f'label=com.docker.compose.service={service}',
                '--format', '{{.Names}}'
            ]
            
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            containers = result.stdout.strip().split('\n')
            if containers and containers[0]:
                return containers[0]

        # 2. Check for ThothAI hardcoded names (thoth-backend, thoth-frontend, etc.)
        # This handles cases where docker-compose.yml defines container_name explicitly,
        # overriding project-based naming defaults.
        thoth_name = f"thoth-{service}"
        # console.print(f"[dim]Checking hardcoded name: {thoth_name}[/dim]")
        
        cmd = ['docker', 'ps', '--filter', f'name=^/{thoth_name}$', '--format', '{{.Names}}']
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            containers = result.stdout.strip().split('\n')
            containers = [c for c in containers if c]
            if containers:
                return containers[0]
        
        # 3. Fallback to stack/project name-based filtering (Legacy/Backup)
        # Identify expected name pattern
        if self.mode == 'swarm':
            # Swarm: stack_service.1.xxx
            filter_name = f"{self.stack_name}_{service}"
        else:
            # Compose: project_service_1 or project-service-1
            # Try generic partial match
            filter_name = f"{self.stack_name}_{service}"
        
        # console.print(f"[dim]Fallback to name filter: {filter_name}[/dim]")
        cmd = ['docker', 'ps', '--filter', f'name={filter_name}', '--format', '{{.Names}}']
        result = self._run_command(cmd)
        
        if result.returncode != 0:
            console.print(f"[red]Error finding container: {result.stderr}[/red]")
            return None
        
        containers = result.stdout.strip().split('\n')
        # Filter out empty strings
        containers = [c for c in containers if c]
        
        if containers:
            # Return the first match
            return containers[0]
        
        console.print(f"[red]No container found for service: {service} (Stack: {self.stack_name})[/red]")
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
        files = self._get_remote_files(self.paths['data_exchange'])
        if files:
            console.print(f"\n[bold]Files in {self.paths['data_exchange']}:[/bold]")
            for f in files:
                console.print(f.strip())
        else:
            console.print(f"[yellow]No files found in {self.paths['data_exchange']}[/yellow]")

    def _get_remote_files(self, path: str) -> List[str]:
        """Helper to get list of files (excluding directories) from remote path."""
        container = self._get_container_name(self.service)
        if not container:
            return []

        # Use find to get only files, maxdepth 1
        cmd = ['docker', 'exec', container, 'find', path, '-maxdepth', '1', '-type', 'f', '-printf', '%f\n']
        # If find is not available or doesn't support -printf (alpine/busybox), fallback to ls -p
        # For compatibility, let's try ls -p and filter
        cmd = ['docker', 'exec', container, 'sh', '-c', f'ls -p {path} | grep -v /']
        
        result = self._run_command(cmd)
        if result.returncode == 0:
            return [f for f in result.stdout.split('\n') if f.strip()]
        return []

    def csv_upload(self, file_path: str):
        """Upload CSV file(s) to data_exchange volume.
        
        Args:
            file_path: 'all', comma-separated list, or single file path.
        """
        container = self._get_container_name(self.service)
        if not container:
            return

        files_to_upload = []

        if file_path == 'all':
            # Priority: 1. data_exchange folder, 2. current folder
            search_dir = Path.cwd() / 'data_exchange'
            if not search_dir.exists():
                search_dir = Path.cwd()
            
            # Common data extensions
            exts = {'.csv', '.sql', '.db', '.sqlite'}
            files_to_upload = [f for f in search_dir.iterdir() if f.is_file() and f.suffix.lower() in exts]
            
            if not files_to_upload:
                console.print(f"[yellow]No data files found in {search_dir}[/yellow]")
                return
        elif ',' in file_path:
            # Comma separated list
            for p in file_path.split(','):
                path = Path(p.strip())
                if path.is_file():
                    files_to_upload.append(path)
                elif path.is_dir():
                    console.print(f"[yellow]Skipping directory: {path}[/yellow]")
                else:
                    console.print(f"[red]File not found: {path}[/red]")
        else:
            # Single file
            path = Path(file_path)
            if path.is_file():
                files_to_upload.append(path)
            elif path.is_dir():
                console.print(f"[yellow]Skipping directory: {path}[/yellow]")
                return
            else:
                console.print(f"[red]File not found: {file_path}[/red]")
                return

        if not files_to_upload:
            console.print("[yellow]No files to upload.[/yellow]")
            return

        for local_path in files_to_upload:
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
                    console.print(f"[red]SCP failed for {filename}: {result.stderr}[/red]")
                    continue
                
                # Docker cp on remote
                cmd = ['docker', 'cp', f'/tmp/{filename}', f'{container}:{remote_path}']
            else:
                # Local docker cp
                cmd = ['docker', 'cp', str(local_path), f'{container}:{remote_path}']
            
            result = self._run_command(cmd)
            if result.returncode == 0:
                console.print(f"[green]✓ Uploaded: {filename}[/green]")
            else:
                console.print(f"[red]Upload failed for {filename}: {result.stderr}[/red]")

    def csv_download(self, filename: str, output_dir: str = '.'):
        """Download CSV file(s) from data_exchange volume.
        
        Args:
            filename: 'all', comma-separated list, or single filename.
            output_dir: Local destination directory.
        """
        container = self._get_container_name(self.service)
        if not container:
            return

        files_to_download = []
        
        if filename == 'all':
            remote_files = self._get_remote_files(self.paths['data_exchange'])
            files_to_download = remote_files
        elif ',' in filename:
            files_to_download = [f.strip() for f in filename.split(',') if f.strip()]
        else:
            files_to_download = [filename]

        if not files_to_download:
            console.print("[yellow]No files to download.[/yellow]")
            return

        out_path = Path(output_dir)
        if not out_path.exists():
            out_path.mkdir(parents=True, exist_ok=True)

        for fname in files_to_download:
            remote_path = f"{self.paths['data_exchange']}/{fname}"
            local_file = out_path / fname
            
            if self.connection == 'ssh':
                # Docker cp to /tmp on remote, then SCP to local
                ssh_config = self.config.get('ssh', {})
                host = f"{ssh_config.get('user')}@{ssh_config.get('host')}"
                
                # Docker cp on remote
                cmd = ['docker', 'cp', f'{container}:{remote_path}', f'/tmp/{fname}']
                result = self._run_command(cmd)
                if result.returncode != 0:
                    console.print(f"[red]Docker cp failed for {fname}: {result.stderr}[/red]")
                    continue
                
                # SCP from remote
                scp_cmd = ['scp']
                if ssh_config.get('key_file'):
                    scp_cmd.extend(['-i', ssh_config['key_file']])
                scp_cmd.extend(['-P', str(ssh_config.get('port', 22))])
                scp_cmd.extend([f"{host}:/tmp/{fname}", str(local_file)])
                
                result = subprocess.run(scp_cmd, capture_output=True, text=True)
            else:
                # Local docker cp
                cmd = ['docker', 'cp', f'{container}:{remote_path}', str(local_file)]
                result = self._run_command(cmd)
            
            if result.returncode == 0:
                console.print(f"[green]✓ Downloaded: {fname} to {local_file}[/green]")
            else:
                console.print(f"[red]Download failed for {fname}: {result.stderr}[/red]")
    
    def csv_delete(self, filename: str):
        """Delete CSV file(s) from data_exchange volume.
        
        Args:
            filename: 'all', comma-separated list, or single filename.
        """
        container = self._get_container_name(self.service)
        if not container:
            return

        files_to_delete = []
        
        if filename == 'all':
            console.print("[yellow]Warning: This will delete ALL files in the data_exchange volume.[/yellow]")
            # In a real interactive CLI we might ask for confirmation, 
            # but for remote/automation tools we usually assume the user knows what they are doing 
            # or rely on a --force flag (not implemented here yet).
            # Let's just proceed for now as per "delete all" request.
            remote_files = self._get_remote_files(self.paths['data_exchange'])
            files_to_delete = remote_files
        elif ',' in filename:
            files_to_delete = [f.strip() for f in filename.split(',') if f.strip()]
        else:
            files_to_delete = [filename]

        if not files_to_delete:
            console.print("[yellow]No files to delete.[/yellow]")
            return

        for fname in files_to_delete:
            remote_path = f"{self.paths['data_exchange']}/{fname}"
            cmd = ['docker', 'exec', container, 'rm', remote_path]
            result = self._run_command(cmd)
            
            if result.returncode == 0:
                console.print(f"[green]✓ Deleted: {fname}[/green]")
            else:
                console.print(f"[red]Delete failed for {fname}: {result.stderr}[/red]")
    
    # === Database Operations ===
    
    def db_list(self):
        """List SQLite databases in shared_data/dev_databases volume."""
        container = self._get_container_name(self.db_service)
        if not container:
            return
        
        target_dir = f"{self.paths['shared_data']}/dev_databases"
        # Use find to recursively list .sqlite and .db files
        # -maxdepth 3 to avoid going too deep if there are many subfolders
        # -name "*.sqlite" -o -name "*.db" to match extensions
        cmd = [
            'docker', 'exec', container, 'sh', '-c',
            f'cd {target_dir} && find . -type f \\( -name "*.sqlite" -o -name "*.db" \\) -print'
        ]
        result = self._run_command(cmd)
        
        if result.returncode == 0:
            console.print(f"\n[bold]Databases in {target_dir}:[/bold]")
            # Filter empty lines and remove leading ./
            files = [f.strip().replace('./', '', 1) for f in result.stdout.split('\n') if f.strip()]
            
            if not files:
                 console.print(f"[yellow]No databases found in {target_dir}[/yellow]")
            else:
                for f in files:
                    if f != 'dev.json': # explicit check just in case
                        console.print(f)
        else:
            # If directory doesn't exist, it might not be an error, just empty
            if "No such file or directory" in result.stderr:
                console.print(f"[yellow]No databases found (Directory {target_dir} does not exist)[/yellow]")
            else:
                console.print(f"[red]Error listing databases: {result.stderr}[/red]")
    
    def db_insert(self, db_path: str):
        """Insert SQLite database into shared_data/dev_databases volume.
        
        Creates a subdirectory with the same name as the database file (without extension)
        and places the database file inside it.
        """
        local_path = Path(db_path)
        if not local_path.exists():
            console.print(f"[red]Database file not found: {db_path}[/red]")
            return
        
        if local_path.name == 'dev.json':
            console.print("[red]Cannot overwrite dev.json[/red]")
            return

        container = self._get_container_name(self.db_service)
        if not container:
            return
        
        # Determine target directory and path
        # Structure: dev_databases/{db_stem}/{db_filename}
        db_stem = local_path.stem
        target_dir = f"{self.paths['shared_data']}/dev_databases/{db_stem}"
        remote_path = f"{target_dir}/{local_path.name}"
        
        # Create directory
        cmd = ['docker', 'exec', container, 'mkdir', '-p', target_dir]
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
            scp_cmd.extend([str(local_path), f"{host}:/tmp/{local_path.name}"])
            
            result = subprocess.run(scp_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[red]SCP failed: {result.stderr}[/red]")
                return
            
            # Docker cp on remote
            cmd = ['docker', 'cp', f'/tmp/{local_path.name}', f'{container}:{remote_path}']
        else:
            # Local docker cp
            cmd = ['docker', 'cp', str(local_path), f'{container}:{remote_path}']
        
        result = self._run_command(cmd)
        if result.returncode == 0:
            console.print(f"[green]✓ Database inserted: {local_path.name}[/green]")
            console.print(f"  Location: {remote_path}")
        else:
            console.print(f"[red]Insert failed: {result.stderr}[/red]")
    
    def db_remove(self, name: str):
        """Remove SQLite database from shared_data/dev_databases volume.
        
        Args:
            name: Filename (e.g. 'db.sqlite'), relative path (e.g. 'dir/db.sqlite'), 
                  or directory name (e.g. 'db_dir').
        """
        if name == 'dev.json':
            console.print("[red]Cannot remove dev.json[/red]")
            return

        container = self._get_container_name(self.db_service)
        if not container:
            return
        
        base_dir = f"{self.paths['shared_data']}/dev_databases"
        
        # We need to handle a few cases:
        # 1. User provides partial path: "folder/db.sqlite" -> remove file, check if folder empty
        # 2. User provides filename only: "db.sqlite" -> check if directly in root (legacy) or in folder with same stem
        # 3. User provides folder name: "folder" -> remove recursively
        
        path_obj = Path(name)
        
        # Case 3: Explicit directory removal (no extension, or known directory)
        # We can try to guess if it's a directory or try to remove as directory first?
        # Let's try to remove as file first, then as directory if file not found?
        # Or simpler: Check if it looks like a file extension
        
        targets_to_try = []
        
        # Case 1 & 2: Looks like a file
        if path_obj.suffix:
            # Exact match
            targets_to_try.append(f"{base_dir}/{name}")
            # Nested match (if name is just filename)
            if len(path_obj.parts) == 1:
                targets_to_try.append(f"{base_dir}/{path_obj.stem}/{name}")
        else:
            # Case 3: Looks like a folder
            targets_to_try.append(f"{base_dir}/{name}")

        
        success = False
        for target in targets_to_try:
            # Check existence first? command 'test -e'
            check_cmd = ['docker', 'exec', container, 'test', '-e', target]
            if self._run_command(check_cmd).returncode == 0:
                # It exists. Is it a file or dir?
                # 'test -d'
                is_dir_cmd = ['docker', 'exec', container, 'test', '-d', target]
                is_dir = self._run_command(is_dir_cmd).returncode == 0
                
                rm_flags = '-rf' if is_dir else '-f'
                rm_cmd = ['docker', 'exec', container, 'rm', rm_flags, target]
                
                result = self._run_command(rm_cmd)
                if result.returncode == 0:
                    console.print(f"[green]✓ Removed: {target}[/green]")
                    success = True
                    
                    # Cleanup parent directory if empty and we just removed a file inside a subdir
                    if not is_dir:
                        parent_dir = str(Path(target).parent)
                        # Ensure we don't remove base_dir
                        if parent_dir != base_dir and parent_dir.startswith(base_dir):
                            # rmdir will only remove if empty
                            cleanup_cmd = ['docker', 'exec', container, 'rmdir', parent_dir]
                            self._run_command(cleanup_cmd) 
                            # Ignore output/errors from cleanup (if not empty, it fails silently-ish)
                    break
        
        if not success:
             console.print(f"[red]Could not find database or directory matching: {name}[/red]")
             console.print(f"Searched in: {base_dir}")

    def prune(self, remove_volumes: bool = True, remove_images: bool = True) -> bool:
        """Remove all Docker artifacts for the configured ThothAI project.
        
        Args:
            remove_volumes: Whether to remove Docker volumes
            remove_images: Whether to remove Docker images
            
        Returns:
            True if cleanup was successful
        """
        success = True
        
        # 1. Stop and remove containers
        console.print("[dim]Stopping and removing containers...[/dim]")
        # We try to remove by label first, then by name
        if self.mode == 'swarm':
            console.print(f"[dim]Removing stack '{self.stack_name}'...[/dim]")
            result = self._run_command(['docker', 'stack', 'rm', self.stack_name])
        else:
            # For compose, we don't have the compose file path here easily 
            # (thothai-data-cli works without the compose file locally)
            # So we remove by filter
            result = self._run_command(['docker', 'ps', '-a', '--filter', f'label=com.docker.compose.project={self.stack_name}', '--format', '{{.ID}}'])
            if result.returncode == 0 and result.stdout.strip():
                ids = result.stdout.strip().split('\n')
                for cid in ids:
                    self._run_command(['docker', 'rm', '-f', cid])
        
        # 2. Final check for any thoth containers
        console.print("[dim]Checking for remaining thoth containers...[/dim]")
        result = self._run_command(['docker', 'ps', '-a', '--filter', 'name=thoth', '--format', '{{.ID}}'])
        if result.returncode == 0 and result.stdout.strip():
            ids = result.stdout.strip().split('\n')
            for cid in ids:
                self._run_command(['docker', 'rm', '-f', cid])
        
        # 3. Remove network
        console.print("[dim]Removing network...[/dim]")
        self._run_command(['docker', 'network', 'rm', 'thoth-network'])
        if self.mode == 'swarm':
             self._run_command(['docker', 'network', 'rm', f'{self.stack_name}_thoth-network'])
        
        # 4. Remove volumes if requested
        if remove_volumes:
            console.print("[dim]Removing volumes...[/dim]")
            volumes = [
                'thoth-secrets',
                'thoth-backend-static',
                'thoth-backend-media',
                'thoth-frontend-cache',
                'thoth-qdrant-data',
                'thoth-shared-data',
                'thoth-data-exchange'
            ]
            for vol in volumes:
                self._run_command(['docker', 'volume', 'rm', vol])
        
        # 5. Remove images if requested
        if remove_images:
            console.print("[dim]Removing ThothAI images...[/dim]")
            result = self._run_command(['docker', 'images', '--filter', 'reference=thothai/*', '--format', '{{.ID}}'])
            if result.returncode == 0 and result.stdout.strip():
                ids = list(set(result.stdout.strip().split('\n')))
                for img_id in ids:
                    self._run_command(['docker', 'rmi', '-f', img_id])
        
        console.print("[green]✓ Cleanup completed[/green]")
        return success
