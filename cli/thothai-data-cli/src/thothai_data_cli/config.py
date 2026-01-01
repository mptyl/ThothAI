# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Configuration management for thothai-data-cli."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()

DEFAULT_CONFIG_PATH = Path.home() / '.thothai-data.yml'


def get_default_config() -> Dict[str, Any]:
    """Return default configuration."""
    return {
        'docker': {
            'connection': 'local',
            'mode': 'swarm',
            'stack_name': 'thothai-swarm',
            'service': 'backend',
            'db_service': 'sql-generator'
        },
        'ssh': {
            'host': '',
            'user': '',
            'port': 22,
            'key_file': ''
        },
        'paths': {
            'data_exchange': '/app/data_exchange',
            'shared_data': '/app/data'
        }
    }


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from YAML file, create interactively if missing."""
    path = config_path or DEFAULT_CONFIG_PATH
    
    # Ensure local data_exchange directory exists in CWD
    data_exchange_local = Path.cwd() / 'data_exchange'
    if not data_exchange_local.exists():
        try:
            data_exchange_local.mkdir(exist_ok=True)
            console.print(f"[green]✓ Created local directory: {data_exchange_local}[/green]")
        except Exception as e:
            console.print(f"[yellow]! Could not create local data_exchange directory: {e}[/yellow]")

    if not path.exists():
        console.print(f"[yellow]Config file not found: {path}[/yellow]")
        if Confirm.ask("Create configuration file?", default=True):
            config = create_interactive_config()
            save_config(config, path)
            console.print(f"[green]✓ Configuration saved to {path}[/green]")
            return config
        else:
            console.print("[yellow]Using default configuration[/yellow]")
            return get_default_config()
    
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def create_interactive_config() -> Dict[str, Any]:
    """Create configuration interactively."""
    console.print("[bold]ThothAI Data CLI Configuration[/bold]\n")
    
    config = get_default_config()
    
    # Docker connection
    connection = Prompt.ask(
        "Docker connection type",
        choices=['local', 'ssh'],
        default='local'
    )
    config['docker']['connection'] = connection
    
    # Docker mode
    mode = Prompt.ask(
        "Docker mode",
        choices=['compose', 'swarm'],
        default='swarm'
    )
    config['docker']['mode'] = mode
    
    # Stack name
    stack_name = Prompt.ask(
        "Stack/project name",
        default='thothai-swarm' if mode == 'swarm' else 'thothai'
    )
    config['docker']['stack_name'] = stack_name
    
    # SSH configuration
    if connection == 'ssh':
        console.print("\n[bold]SSH Configuration[/bold]")
        config['ssh']['host'] = Prompt.ask("SSH host")
        config['ssh']['user'] = Prompt.ask("SSH user")
        config['ssh']['port'] = int(Prompt.ask("SSH port", default="22"))
        
        key_file = Prompt.ask("SSH key file (leave empty for default)", default="")
        if key_file:
            config['ssh']['key_file'] = key_file
    
    return config


def save_config(config: Dict[str, Any], path: Path = DEFAULT_CONFIG_PATH):
    """Save configuration to YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def show_config(config: Dict[str, Any]):
    """Display current configuration."""
    from rich.table import Table
    
    table = Table(title="ThothAI Data CLI Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Connection", config['docker']['connection'])
    table.add_row("Mode", config['docker']['mode'])
    table.add_row("Stack Name", config['docker']['stack_name'])
    table.add_row("Service", config['docker']['service'])
    table.add_row("DB Service", config['docker']['db_service'])
    
    if config['docker']['connection'] == 'ssh':
        table.add_row("", "")
        table.add_row("[bold]SSH Settings[/bold]", "")
        table.add_row("Host", config['ssh']['host'])
        table.add_row("User", config['ssh']['user'])
        table.add_row("Port", str(config['ssh']['port']))
        if config['ssh'].get('key_file'):
            table.add_row("Key File", config['ssh']['key_file'])
    
    console.print(table)
