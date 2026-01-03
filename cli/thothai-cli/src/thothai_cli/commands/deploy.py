# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Deploy commands: up, down, status, ps, logs, update."""

import click
from rich.console import Console
from pathlib import Path

from ..core.docker_manager import DockerManager
from ..core.config_manager import ConfigManager

console = Console()


def get_docker_manager() -> DockerManager:
    """Get configured Docker manager instance."""
    config_path = Path.cwd() / 'config.yml.local'
    if not config_path.exists():
        console.print("[red]Error: config.yml.local not found[/red]")
        console.print("Run [cyan]thothai init[/cyan] first")
        raise click.Abort()
    
    config_mgr = ConfigManager(config_path)
    return DockerManager(config_mgr)


@click.command()
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def up(server):
    """Pull images and start Docker containers."""
    try:
        console.print("\n[bold blue]Starting ThothAI deployment...[/bold blue]\n")
        docker_mgr = get_docker_manager()
        
        success = docker_mgr.up(server=server)
        
        if success:
            console.print("\n[bold green]✓ ThothAI is running![/bold green]")
            docker_mgr.print_access_info()
        else:
            console.print("\n[bold red]✗ Deployment failed[/bold red]")
            raise click.Abort()
    
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def down(server):
    """Stop and remove Docker containers."""
    try:
        console.print("\n[bold yellow]Stopping ThothAI...[/bold yellow]\n")
        docker_mgr = get_docker_manager()
        
        success = docker_mgr.down(server=server)
        
        if success:
            console.print("\n[bold green]✓ ThothAI stopped[/bold green]")
        else:
            console.print("\n[bold red]✗ Stop failed[/bold red]")
            raise click.Abort()
    
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def status(server):
    """Show running container status."""
    try:
        docker_mgr = get_docker_manager()
        docker_mgr.status(server=server)
    
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
@click.argument('service', required=False)
@click.option('--tail', default=50, help='Number of lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def logs(service, tail, follow, server):
    """View container logs.
    
    \b
    Examples:
        thothai logs              # All services
        thothai logs backend      # Specific service
        thothai logs -f backend   # Follow backend logs
    """
    try:
        docker_mgr = get_docker_manager()
        docker_mgr.logs(service, tail, follow, server=server)
    
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show all containers including stopped')
def ps(server, show_all):
    """Show active services and their details.
    
    Similar to 'docker compose ps' but with enhanced formatting.
    Automatically detects Swarm mode and shows stack services.
    
    \\b
    Examples:
        thothai ps                   # Local containers
        thothai ps --all             # Include stopped containers
        thothai ps --server user@host  # Remote containers
    """
    try:
        docker_mgr = get_docker_manager()
        docker_mgr.ps(server=server, show_all=show_all)
    
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
def update(server):
    """Update containers to latest images.
    
    Pulls the latest images from Docker Hub and recreates containers.
    This is a manual update - no automatic updates are performed.
    """
    try:
        console.print("\n[bold blue]Updating ThothAI to latest version...[/bold blue]\n")
        docker_mgr = get_docker_manager()
        
        success = docker_mgr.update(server=server)
        
        if success:
            console.print("\n[bold green]✓ Update complete![/bold green]")
            docker_mgr.print_access_info()
        else:
            console.print("\n[bold red]✗ Update failed[/bold red]")
            raise click.Abort()
    
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()
