# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Prune command: Remove Docker artifacts for a ThothAI project."""

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


@click.command('prune')
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
@click.option('--yes', '-y', 'skip_confirm', is_flag=True, help='Skip confirmation prompt')
@click.option('--volumes/--no-volumes', default=True, help='Include/exclude volumes (default: include)')
@click.option('--images/--no-images', default=True, help='Include/exclude images (default: include)')
def prune_cmd(server, skip_confirm, volumes, images):
    """Remove all Docker artifacts for this ThothAI project.
    
    This command removes containers, networks, volumes (optional), and images
    related to the ThothAI deployment defined in the current directory.
    
    \\b
    Examples:
        thothai prune              # Interactive confirmation
        thothai prune --yes        # Skip confirmation
        thothai prune --no-volumes # Keep persistent data
        thothai prune --server user@host  # Remote cleanup
    """
    try:
        docker_mgr = get_docker_manager()
        mode = docker_mgr.config_mgr.get('docker', {}).get('deployment_mode', 'compose')
        
        if mode == 'swarm':
            console.print("[yellow]Swarm mode detected. Use [cyan]thothai swarm prune[/cyan] instead.[/yellow]")
            raise click.Abort()
        
        # Confirmation prompt
        if not skip_confirm:
            console.print("\n[bold red]⚠ WARNING: This will remove all ThothAI Docker artifacts![/bold red]\n")
            console.print("The following will be removed:")
            console.print("  • All ThothAI containers")
            console.print("  • ThothAI network (thoth-network)")
            if volumes:
                console.print("  • [red]All ThothAI volumes (including data!)[/red]")
            if images:
                console.print("  • ThothAI Docker images")
            console.print("  • Generated configuration files")
            console.print()
            
            if not click.confirm("Are you sure you want to proceed?"):
                console.print("[yellow]Aborted.[/yellow]")
                raise click.Abort()
        
        console.print("\n[bold blue]Cleaning up ThothAI Docker artifacts...[/bold blue]\n")
        
        success = docker_mgr.prune(server=server, remove_volumes=volumes, remove_images=images)
        
        if success:
            console.print("\n[bold green]✓ Cleanup complete![/bold green]")
        else:
            console.print("\n[bold red]✗ Cleanup failed or incomplete[/bold red]")
            raise click.Abort()
    
    except click.Abort:
        raise
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@click.command('prune')
@click.option('--server', help='SSH URL for remote server (e.g., user@host)')
@click.option('--yes', '-y', 'skip_confirm', is_flag=True, help='Skip confirmation prompt')
@click.option('--volumes/--no-volumes', default=True, help='Include/exclude volumes (default: include)')
@click.option('--images/--no-images', default=True, help='Include/exclude images (default: include)')
def swarm_prune_cmd(server, skip_confirm, volumes, images):
    """Remove all Docker Swarm artifacts for this ThothAI project.
    
    This command removes the stack, secrets, configs, volumes (optional), 
    and images related to the ThothAI Swarm deployment.
    
    \\b
    Examples:
        thothai swarm prune              # Interactive confirmation
        thothai swarm prune --yes        # Skip confirmation  
        thothai swarm prune --no-volumes # Keep persistent data
        thothai swarm prune --server user@host  # Remote cleanup
    """
    try:
        docker_mgr = get_docker_manager()
        swarm_env = docker_mgr._get_swarm_env()
        stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
        
        # Confirmation prompt
        if not skip_confirm:
            console.print("\n[bold red]⚠ WARNING: This will remove all ThothAI Swarm artifacts![/bold red]\n")
            console.print(f"Stack: [cyan]{stack_name}[/cyan]")
            console.print("\nThe following will be removed:")
            console.print(f"  • Stack '{stack_name}' and all its services")
            console.print(f"  • Swarm secrets ({stack_name}_thoth_*)")
            console.print(f"  • Swarm configs ({stack_name}_thoth_*)")
            if volumes:
                console.print("  • [red]All ThothAI volumes (including data!)[/red]")
            if images:
                console.print("  • ThothAI Docker images")
            console.print()
            
            if not click.confirm("Are you sure you want to proceed?"):
                console.print("[yellow]Aborted.[/yellow]")
                raise click.Abort()
        
        console.print("\n[bold blue]Cleaning up ThothAI Swarm artifacts...[/bold blue]\n")
        
        success = docker_mgr.swarm_prune(server=server, remove_volumes=volumes, remove_images=images)
        
        if success:
            console.print("\n[bold green]✓ Swarm cleanup complete![/bold green]")
        else:
            console.print("\n[bold red]✗ Swarm cleanup failed or incomplete[/bold red]")
            raise click.Abort()
    
    except click.Abort:
        raise
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()
