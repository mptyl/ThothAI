# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Swarm commands: deploy, status, ps, update, rollback."""

import click
from rich.console import Console
from ..core.docker_manager import DockerManager
from ..core.config_manager import ConfigManager
from .prune import swarm_prune_cmd
from pathlib import Path

console = Console()


def get_docker_manager() -> DockerManager:
    """Get configured Docker manager instance."""
    config_path = Path.cwd() / 'config.yml.local'
    if not config_path.exists():
        console.print("[red]Error: config.yml.local not found[/red]")
        console.print("Run [cyan]thothai init[/cyan] first")
        raise click.Abort()
    
    config_mgr = ConfigManager(config_path)
    
    # Ensure consistent stack name default
    raw_config = config_mgr.config
    deployment_mode = raw_config.get('docker', {}).get('deployment_mode', 'swarm')
    default_stack = 'thothai-swarm' if deployment_mode == 'swarm' else 'thothai'
    
    # Update config object with explicit stack name if not present
    if 'docker' not in raw_config:
        raw_config['docker'] = {}
    
    if 'stack_name' not in raw_config['docker']:
        raw_config['docker']['stack_name'] = default_stack
        
    return DockerManager(config_mgr)


@click.group('swarm')
def swarm_group():
    """Docker Swarm deployment commands."""
    pass


@swarm_group.command('deploy')
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def deploy(server):
    """Deploy ThothAI to Docker Swarm."""
    try:
        docker_mgr = get_docker_manager()
        success = docker_mgr.swarm_up(server=server)
        
        if success:
            console.print("\n[bold green]✓ ThothAI is deployed to Swarm![/bold green]")
            docker_mgr.print_access_info(is_swarm=True)
        else:
            console.print("\n[bold red]✗ Swarm deployment failed[/bold red]")
            raise click.Abort()
            
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@swarm_group.command('down')
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def down(server):
    """Remove ThothAI stack from Docker Swarm."""
    try:
        docker_mgr = get_docker_manager()
        success = docker_mgr.swarm_down(server=server)
        
        if success:
            console.print("\n[bold green]✓ ThothAI stack removed[/bold green]")
        else:
            console.print("\n[bold red]✗ Failed to remove stack[/bold red]")
            raise click.Abort()
            
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@swarm_group.command('status')
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def swarm_status_cmd(server):
    """Show Swarm services status."""
    try:
        docker_mgr = get_docker_manager()
        docker_mgr.swarm_status(server=server)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@swarm_group.command('ps')
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
@click.option('--service', '-s', help='Show tasks for specific service only')
def swarm_ps_cmd(server, service):
    """Show Swarm stack services and tasks.
    
    \\b
    Examples:
        thothai swarm ps                    # All stack services
        thothai swarm ps -s backend         # Tasks for backend service only
        thothai swarm ps --server user@host # Remote stack status
    """
    try:
        docker_mgr = get_docker_manager()
        docker_mgr.swarm_ps(service=service, server=server)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@swarm_group.command('update')
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def swarm_update_cmd(server):
    """Update Swarm services to latest images."""
    try:
        docker_mgr = get_docker_manager()
        success = docker_mgr.swarm_update(server=server)
        if success:
            console.print("\n[bold green]✓ Swarm services updated[/bold green]")
        else:
            console.print("\n[bold red]✗ Update failed[/bold red]")
            raise click.Abort()
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@swarm_group.command('rollback')
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def rollback(server):
    """Rollback Swarm services to previous version."""
    try:
        docker_mgr = get_docker_manager()
        success = docker_mgr.swarm_rollback(server=server)
        if success:
            console.print("\n[bold green]✓ Swarm services rolled back[/bold green]")
        else:
            console.print("\n[bold red]✗ Rollback failed[/bold red]")
            raise click.Abort()
            raise click.Abort()
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@swarm_group.command('logs')
@click.argument('service', required=False, default='backend')
@click.option('--tail', default=50, help='Number of lines to show')
@click.option('-f', '--follow', is_flag=True, help='Follow log output')
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def logs(service, tail, follow, server):
    """View Swarm service logs (default: backend)."""
    try:
        docker_mgr = get_docker_manager()
        docker_mgr.swarm_logs(service=service, tail=tail, follow=follow, server=server)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


# Register prune subcommand
swarm_group.add_command(swarm_prune_cmd)
