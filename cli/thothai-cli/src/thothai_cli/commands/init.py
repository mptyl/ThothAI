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

from ..core.config_manager import ConfigManager


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
        ('data', 'data'),
        ('setup_csv', 'setup_csv'),
    ]
    
    if mode == 'swarm':
        templates_to_copy.extend([
            ('docker-stack.yml', 'docker-stack.yml'),
            ('swarm_config.env', 'swarm_config.env'),
        ])
    
    try:
        # Access embedded templates
        from .. import templates as templates_module
        templates_root = importlib.resources.files(templates_module)
        
        for template_name, target_name in templates_to_copy:
            source = templates_root / template_name
            target = target_dir / target_name
            
            if target.exists():
                console.print(f"[yellow]⚠ {target_name} already exists, skipping[/yellow]")
                continue
            
            # Use importlib.resources.as_file to get a real Path for shutil
            with importlib.resources.as_file(source) as source_path:
                if source_path.is_dir():
                    shutil.copytree(source_path, target)
                    console.print(f"[green]✓[/green] Created {target_name}/ directory")
                else:
                    if template_name == 'config.yml':
                        # Customize deployment mode in config.yml.local
                        content = source_path.read_text(encoding='utf-8')
                        content = content.replace('deployment_mode: "compose"', f'deployment_mode: "{mode}"')
                        target.write_text(content, encoding='utf-8')
                    else:
                        shutil.copy(source_path, target)
                    console.print(f"[green]✓[/green] Created {target_name}")
        
        # Copy docs directory with user manual only
        # The file is included via force-include in pyproject.toml
        import thothai_cli
        package_dir = Path(thothai_cli.__file__).parent
        docs_source = package_dir / 'docs' / 'CLI_USER_MANUAL_IT.md'
        docs_target = target_dir / 'docs'
        
        if docs_target.exists():
            console.print(f"[yellow]⚠ docs already exists, skipping[/yellow]")
        elif docs_source.exists():
            docs_target.mkdir(parents=True, exist_ok=True)
            shutil.copy(docs_source, docs_target / 'CLI_USER_MANUAL_IT.md')
            console.print(f"[green]✓[/green] Created docs/ directory")
        else:
            console.print(f"[yellow]⚠ docs source not found, skipping[/yellow]")

        
        # Create .gitignore
        gitignore_content = """# ThothAI
config.yml.local
.env.docker
swarm_config.env
data/
data_exchange/
*.log
"""
        gitignore_path = target_dir / '.gitignore'
        if not gitignore_path.exists():
            gitignore_path.write_text(gitignore_content, encoding='utf-8')
            console.print(f"[green]✓[/green] Created .gitignore")
        
        # Create data_exchange directory
        data_exchange = target_dir / 'data_exchange'
        data_exchange.mkdir(exist_ok=True)
        if not (data_exchange / '.gitkeep').exists():
            (data_exchange / '.gitkeep').touch()
        console.print(f"[green]✓[/green] Created data_exchange/ directory")
        
        # Generate .env.docker immediately to allow user inspection/editing
        try:
            config_path = target_dir / 'config.yml.local'
            if config_path.exists():
                console.print("[dim]Generating initial .env.docker...[/dim]")
                # We need to ensure we don't crash if config is invalid (default template should be valid enough)
                # But ConfigManager might validate?? No, generate_env_docker just reads values.
                cm = ConfigManager(config_path)
                if cm.generate_env_docker():
                    console.print(f"[green]✓[/green] Generated .env.docker")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not generate .env.docker: {e}[/yellow]")
        
        console.print("\n[bold green]✓ Initialization complete![/bold green]\n")
        console.print("[bold]Next steps:[/bold]")
        console.print(f"1. Edit [cyan]{target_dir}/config.yml.local[/cyan] with your API keys")
        console.print(f"2. Run [cyan]thothai up[/cyan] to deploy")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error during initialization:[/bold red] {e}")
        raise click.Abort()
