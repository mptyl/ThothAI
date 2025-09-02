# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib import messages
from thoth_core.models import SqlDb, Workspace
from thoth_core.thoth_ai.thoth_workflow.create_db_scope import generate_scope as generate_scope_action


class Command(BaseCommand):
    help = 'Generate scope for specified databases using AI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace',
            type=int,
            help='Workspace ID to use for generation'
        )
        parser.add_argument(
            '--database',
            type=str,
            help='Database name to generate scope for'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate scope for all databases'
        )

    def handle(self, *args, **options):
        workspace_id = options.get('workspace')
        database_name = options.get('database')
        generate_all = options.get('all')

        if not workspace_id:
            self.stdout.write(self.style.ERROR('Workspace ID is required'))
            raise CommandError('Please specify --workspace')

        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            raise CommandError(f'Workspace with ID {workspace_id} does not exist')

        # Build queryset
        if generate_all:
            databases = SqlDb.objects.all()
            self.stdout.write(f'Generating scope for all {databases.count()} databases...')
        elif database_name:
            try:
                databases = SqlDb.objects.filter(name=database_name)
                if not databases.exists():
                    raise CommandError(f'Database "{database_name}" not found')
            except SqlDb.DoesNotExist:
                raise CommandError(f'Database "{database_name}" not found')
        else:
            # Default to workspace database
            databases = SqlDb.objects.filter(id=workspace.sql_db.id)
            self.stdout.write(f'Generating scope for workspace database: {workspace.sql_db.name}')

        # Create mock objects for the admin action
        class MockRequest:
            def __init__(self, workspace):
                self.current_workspace = workspace
        
        class MockModelAdmin:
            def message_user(self, request, message, level=messages.INFO):
                # Print messages to stdout for logging
                level_name = {
                    messages.SUCCESS: 'SUCCESS',
                    messages.WARNING: 'WARNING',
                    messages.ERROR: 'ERROR',
                    messages.INFO: 'INFO'
                }.get(level, 'INFO')
                print(f"[{level_name}] {message}")

        mock_request = MockRequest(workspace)
        mock_modeladmin = MockModelAdmin()

        # Call the action
        try:
            with transaction.atomic():
                generate_scope_action(mock_modeladmin, mock_request, databases)
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully generated scope for {databases.count()} database(s)'
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating scope: {str(e)}'))
            raise CommandError(str(e))