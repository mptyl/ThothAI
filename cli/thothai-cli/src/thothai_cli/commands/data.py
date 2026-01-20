# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Data management commands: csv and db operations."""

import click
from rich.console import Console
from pathlib import Path
from ..core.config_manager import ConfigManager
from thothai_cli_core.docker_ops import DockerOperations

console = Console()


def get_docker_ops():
    """Helper to initialize DockerOperations from thothai-cli config."""
    env_path = Path.cwd() / '.env.docker'
    if not env_path.exists():
        console.print("[red]Error: .env.docker not found[/red]")
        return None
    
    try:
        config_mgr = ConfigManager(env_path)
        
        # Get deployment mode and stack name from .env.docker
        deployment_mode = config_mgr.deployment_mode
        stack_name = config_mgr.stack_name
        
        # Map thothai-cli config to what DockerOperations expects
        docker_ops_config = {
            'docker': {
                'connection': 'local',
                'mode': deployment_mode,
                'stack_name': stack_name,
                'service': 'backend',
                'db_service': 'sql-generator'
            },
            'paths': {
                'data_exchange': '/app/data_exchange',
                'shared_data': '/app/data'
            }
        }
        return DockerOperations(docker_ops_config)
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        return None


@click.group('csv')
def csv_group():
    """Manage CSV files in data_exchange volume."""
    pass


@csv_group.command('list')
def csv_list():
    """List CSV files in data_exchange volume."""
    ops = get_docker_ops()
    if ops:
        ops.csv_list()


@csv_group.command('upload')
@click.argument('file', type=click.Path(exists=True))
def csv_upload(file):
    """Upload CSV file to data_exchange volume."""
    ops = get_docker_ops()
    if ops:
        ops.csv_upload(file)


@csv_group.command('download')
@click.argument('filename')
@click.option('-o', '--output', default='data_exchange', help='Output directory')
def csv_download(filename, output):
    """Download CSV file from data_exchange volume."""
    ops = get_docker_ops()
    if ops:
        ops.csv_download(filename, output)


@csv_group.command('delete')
@click.argument('filename')
def csv_delete(filename):
    """Delete CSV file from data_exchange volume."""
    ops = get_docker_ops()
    if ops:
        ops.csv_delete(filename)


@click.group('db')
def db_group():
    """Manage SQLite databases in shared_data volume."""
    pass


@db_group.command('list')
def db_list():
    """List SQLite databases in shared_data volume."""
    ops = get_docker_ops()
    if ops:
        ops.db_list()


@db_group.command('insert')
@click.argument('path', type=click.Path(exists=True))
def db_insert(path):
    """Insert SQLite database into shared_data volume."""
    ops = get_docker_ops()
    if ops:
        ops.db_insert(path)


@db_group.command('remove')
@click.argument('name')
def db_remove(name):
    """Remove SQLite database from shared_data volume."""
    ops = get_docker_ops()
    if ops:
        ops.db_remove(name)
