# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Init command: Initialize ThothAI project."""

import click
from pathlib import Path
from rich.console import Console
import shutil
import importlib.resources

console = Console()


@click.command('init')
@click.option('--dir', 'directory', type=click.Path(), default='.',
              help='Directory to initialize (default: current)')
@click.option('--mode', type=click.Choice(['compose', 'swarm']), default='compose',
              help='Deployment mode')
@click.pass_context
def init_cmd(ctx, directory, mode):
    """Initialize a new ThothAI project.
    
    Creates configuration files and Docker orchestration files
    in the specified directory.
    """
    target_dir = Path(directory).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"\n[bold blue]Initializing ThothAI in {target_dir}[/bold blue]\n")
    
    # Copy template files
    templates_to_copy = [
        ('config.yml', 'config.yml.local'),
        ('docker-compose.yml', 'docker-compose.yml'),
    ]
    
    if mode == 'swarm':
        templates_to_copy.extend([
            ('docker-stack.yml', 'docker-stack.yml'),
            ('swarm_config.env', 'swarm_config.env'),
        ])
    
    try:
        # Access embedded templates
        from .. import templates as templates_module
        templates_path = Path(importlib.resources.files(templates_module))
        
        for template_name, target_name in templates_to_copy:
            source = templates_path / template_name
            target = target_dir / target_name
            
            if target.exists():
                console.print(f"[yellow]⚠ {target_name} already exists, skipping[/yellow]")
                continue
            
            if template_name == 'config.yml':
                # Customize deployment mode in config.yml.local
                content = source.read_text()
                content = content.replace('deployment_mode: "compose"', f'deployment_mode: "{mode}"')
                target.write_text(content)
            else:
                shutil.copy(source, target)
            console.print(f"[green]✓[/green] Created {target_name}")
        
        # Create .gitignore
        gitignore_content = """# ThothAI
config.yml.local
.env.docker
swarm_config.env
data_exchange/
*.log
"""
        gitignore_path = target_dir / '.gitignore'
        if not gitignore_path.exists():
            gitignore_path.write_text(gitignore_content)
            console.print(f"[green]✓[/green] Created .gitignore")
        
        # Create data_exchange directory
        data_exchange = target_dir / 'data_exchange'
        data_exchange.mkdir(exist_ok=True)
        console.print(f"[green]✓[/green] Created data_exchange/ directory")
        
        console.print("\n[bold green]✓ Initialization complete![/bold green]\n")
        console.print("[bold]Next steps:[/bold]")
        console.print(f"1. Edit [cyan]{target_dir}/config.yml.local[/cyan] with your API keys")
        console.print(f"2. Run [cyan]thothai up[/cyan] to deploy")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error during initialization:[/bold red] {e}")
        raise click.Abort()
