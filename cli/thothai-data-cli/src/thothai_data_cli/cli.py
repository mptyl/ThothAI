# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""CLI commands for thothai-data-cli."""

import click
from pathlib import Path
from .config import load_config, show_config
from thothai_cli_core.docker_ops import DockerOperations
from rich.console import Console
from rich.markdown import Markdown

console = Console()


@click.group()
@click.option('--config', '-c', type=click.Path(), help='Path to config file')
@click.pass_context
def main(ctx, config):
    """ThothAI Data CLI - Manage CSV files and SQLite databases in Docker."""
    ctx.ensure_object(dict)
    
    config_path = Path(config) if config else None
    ctx.obj['config'] = load_config(config_path)
    ctx.obj['docker'] = DockerOperations(ctx.obj['config'])


# === CSV Commands ===

@main.group()
def csv():
    """Manage CSV files in data_exchange volume."""
    pass


@csv.command('list')
@click.pass_context
def csv_list(ctx):
    """List CSV files in data_exchange volume."""
    ctx.obj['docker'].csv_list()


@csv.command('upload')
@click.argument('file', type=click.Path(exists=True))
@click.pass_context
def csv_upload(ctx, file):
    """Upload CSV file to data_exchange volume."""
    ctx.obj['docker'].csv_upload(file)


@csv.command('download')
@click.argument('filename')
@click.option('-o', '--output', default='.', help='Output directory')
@click.pass_context
def csv_download(ctx, filename, output):
    """Download CSV file from data_exchange volume."""
    ctx.obj['docker'].csv_download(filename, output)


@csv.command('delete')
@click.argument('filename')
@click.pass_context
def csv_delete(ctx, filename):
    """Delete CSV file from data_exchange volume."""
    ctx.obj['docker'].csv_delete(filename)


# === Database Commands ===

@main.group()
def db():
    """Manage SQLite databases in shared_data volume."""
    pass


@db.command('list')
@click.pass_context
def db_list(ctx):
    """List SQLite databases in shared_data volume."""
    ctx.obj['docker'].db_list()


@db.command('insert')
@click.argument('path', type=click.Path(exists=True))
@click.pass_context
def db_insert(ctx, path):
    """Insert SQLite database into shared_data volume.
    
    Creates directory structure: /app/data/{name}/{name}.sqlite
    """
    ctx.obj['docker'].db_insert(path)


@db.command('remove')
@click.argument('name')
@click.pass_context
def db_remove(ctx, name):
    """Remove SQLite database from shared_data volume."""
    ctx.obj['docker'].db_remove(name)


# === Config Commands ===

@main.group()
def config():
    """Manage CLI configuration."""
    pass


@config.command('show')
@click.pass_context
def config_show(ctx):
    """Show current configuration."""
    show_config(ctx.obj['config'])


@config.command('test')
@click.pass_context
def config_test(ctx):
    """Test Docker connection."""
    ctx.obj['docker'].test_connection()


@main.command('manual')
def show_manual():
    """Mostra il manuale utente completo."""
    manual_path = Path(__file__).parent / "docs" / "USER_MANUAL_IT.md"
    if manual_path.exists():
        with open(manual_path, 'r') as f:
            content = f.read()
        
        console.print(Markdown(content))
    else:
        console.print("[red]Errore: Manuale utente non trovato.[/red]")


@main.command('prune')
@click.option('-y', '--yes', is_flag=True, help='Skip confirmation prompt')
@click.option('--volumes/--no-volumes', default=True, help='Include/exclude volumes (default: include)')
@click.option('--images/--no-images', default=True, help='Include/exclude images (default: include)')
@click.pass_context
def prune(ctx, yes, volumes, images):
    """Remove all Docker artifacts for this ThothAI project.
    
    This command removes containers, networks, volumes (optional), and images
    related to the ThothAI deployment.
    """
    if not yes:
        click.confirm(
            "\n[yellow]WARNING: This will remove ThothAI containers and networks.[/yellow]\n"
            "Are you sure you want to proceed?",
            abort=True
        )
        
        if volumes:
             click.confirm(
                "[red]CRITICAL: This will PERMANENTLY DELETE all persistent data (databases and CSVs).[/red]\n"
                "Are you REALLY sure?",
                abort=True
            )

    ctx.obj['docker'].prune(remove_volumes=volumes, remove_images=images)


if __name__ == '__main__':
    main()
