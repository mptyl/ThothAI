# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""Main CLI entry point for thothai-cli."""

import click
from rich.console import Console
from pathlib import Path

from .commands import init, deploy, swarm, data, config

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="thothai")
@click.pass_context
def main(ctx):
    """ThothAI - Lightweight installation and management CLI.
    
    Deploy and manage ThothAI without cloning the repository.
    """
    ctx.ensure_object(dict)
    ctx.obj['console'] = console


# Register command groups
main.add_command(init.init_cmd)
main.add_command(deploy.up)
main.add_command(deploy.down)
main.add_command(deploy.status)
main.add_command(deploy.logs)
main.add_command(deploy.update)
main.add_command(swarm.swarm_group)
main.add_command(data.csv_group)
main.add_command(data.db_group)
main.add_command(config.config_group)


if __name__ == '__main__':
    main()
