# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand
from django.db import transaction
from thoth_core.models import Workspace, SqlDb
from thoth_core.thoth_ai.thoth_workflow.create_db_scope import generate_scope


class Command(BaseCommand):
    help = 'Generate AI-powered scope for demo workspace databases (ID=1)'

    def handle(self, *args, **options):
        try:
            # Get the demo workspace (ID=1)
            workspace = Workspace.objects.get(id=1)
            self.stdout.write(f'Found demo workspace: {workspace.name}')
            
            # Check if workspace has required settings
            if not workspace.setting or not workspace.setting.comment_model:
                self.stdout.write(
                    self.style.WARNING(
                        'Workspace does not have AI model configured. Skipping scope generation.'
                    )
                )
                return
            
            # Get all databases in the workspace
            databases = SqlDb.objects.filter(workspace=workspace)
            
            if not databases.exists():
                self.stdout.write(
                    self.style.WARNING('No databases found in demo workspace')
                )
                return
            
            self.stdout.write(f'Processing {databases.count()} database(s)...')
            
            # Create a mock request object with the workspace
            class MockRequest:
                def __init__(self, workspace):
                    self.current_workspace = workspace
                    self.META = {}
            
            mock_request = MockRequest(workspace)
            
            # Process each database
            success_count = 0
            for db in databases:
                if db.scope:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Database {db.name} already has scope')
                    )
                    continue
                
                self.stdout.write(f'Generating scope for: {db.name}...')
                try:
                    # Call the scope generation function
                    queryset = SqlDb.objects.filter(id=db.id)
                    generate_scope(None, mock_request, queryset)
                    
                    # Refresh from database
                    db.refresh_from_db()
                    if db.scope:
                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Generated scope for {db.name}')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'✗ No scope generated for {db.name}')
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error processing {db.name}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nCompleted: {success_count} database(s) processed successfully'
                )
            )
            
        except Workspace.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Demo workspace (ID=1) not found. Please run load_defaults first.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )