# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Config commands: show, validate, test."""

import click
from rich.console import Console
from rich.table import Table
from pathlib import Path

from ..core.config_manager import ConfigManager

console = Console()


@click.group('config')
def config_group():
    """Configuration management commands."""
    pass


@config_group.command('show')
def config_show():
    """Show current configuration."""
    config_path = Path.cwd() / 'config.yml.local'
    
    if not config_path.exists():
        console.print("[red]config.yml.local not found[/red]")
        return
    
    config_mgr = ConfigManager(config_path)
    
    table = Table(title="ThothAI Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # AI Providers
    providers = config_mgr.get('ai_providers', {})
    enabled_providers = [name for name, data in providers.items() if data.get('enabled')]
    table.add_row("AI Providers", ", ".join(enabled_providers) if enabled_providers else "None")
    
    # Embedding
    embedding = config_mgr.get('embedding', {})
    table.add_row("Embedding Provider", embedding.get('provider', 'Not set'))
    
    # Ports
    ports = config_mgr.get('ports', {})
    table.add_row("Frontend Port", str(ports.get('frontend', 3040)))
    table.add_row("Backend Port", str(ports.get('nginx', 8040)))
    
    console.print(table)


@config_group.command('validate')
def config_validate():
    """Validate configuration."""
    config_path = Path.cwd() / 'config.yml.local'
    
    if not config_path.exists():
        console.print("[red]config.yml.local not found[/red]")
        raise click.Abort()
    
    config_mgr = ConfigManager(config_path)
    
    console.print("\n[bold]Validating configuration...[/bold]\n")
    
    if config_mgr.validate():
        console.print("[bold green]✓ Configuration is valid[/bold green]")
    else:
        console.print("\n[bold red]✗ Configuration has errors[/bold red]")
        raise click.Abort()


@config_group.command('test')
def config_test():
    """Test Docker connection."""
    import subprocess
    
    console.print("\n[bold]Testing Docker connection...[/bold]\n")
    
    result = subprocess.run(['docker', 'info'], capture_output=True)
    
    if result.returncode == 0:
        console.print("[bold green]✓ Docker is running[/bold green]")
    else:
        console.print("[bold red]✗ Docker is not running or not accessible[/bold red]")
        raise click.Abort()
