# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand
from django.contrib import messages as django_messages
from thoth_core.models import Workspace, SqlDb
from thoth_core.thoth_ai.thoth_workflow.generate_db_documentation import generate_db_documentation


class Command(BaseCommand):
    help = 'Generate AI-powered documentation for demo workspace databases (ID=1)'

    def handle(self, *args, **options):
        try:
            # Get the demo workspace (ID=1)
            workspace = Workspace.objects.get(id=1)
            self.stdout.write(f'Found demo workspace: {workspace.name}')
            
            # Check if workspace has required settings
            if not workspace.setting or not workspace.setting.comment_model:
                self.stdout.write(
                    self.style.WARNING(
                        'Workspace does not have AI model configured. Skipping documentation generation.'
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
            
            # Create a mock request object with the workspace and messages support
            class MockRequest:
                def __init__(self, workspace):
                    self.current_workspace = workspace
                    self.META = {}
                    self._messages = []
            
            # Create a messages collector
            class MessageCollector:
                def __init__(self, command):
                    self.command = command
                    self.messages = []
                
                def add_message(self, request, level, message, extra_tags='', fail_silently=False):
                    self.messages.append({'level': level, 'message': message})
                    # Print to console
                    if level == django_messages.SUCCESS:
                        self.command.stdout.write(self.command.style.SUCCESS(f'  {message}'))
                    elif level == django_messages.ERROR:
                        self.command.stdout.write(self.command.style.ERROR(f'  {message}'))
                    elif level == django_messages.WARNING:
                        self.command.stdout.write(self.command.style.WARNING(f'  {message}'))
                    else:
                        self.command.stdout.write(f'  {message}')
                
                def success(self, request, message):
                    self.add_message(request, django_messages.SUCCESS, message)
                
                def error(self, request, message):
                    self.add_message(request, django_messages.ERROR, message)
                
                def warning(self, request, message):
                    self.add_message(request, django_messages.WARNING, message)
                
                def info(self, request, message):
                    self.add_message(request, django_messages.INFO, message)
            
            mock_request = MockRequest(workspace)
            message_collector = MessageCollector(self)
            
            # Temporarily replace the messages framework
            original_add_message = django_messages.add_message
            original_success = django_messages.success
            original_error = django_messages.error
            original_warning = django_messages.warning
            original_info = django_messages.info
            
            django_messages.add_message = message_collector.add_message
            django_messages.success = message_collector.success
            django_messages.error = message_collector.error
            django_messages.warning = message_collector.warning
            django_messages.info = message_collector.info
            
            try:
                # Process each database
                success_count = 0
                for db in databases:
                    self.stdout.write(f'\nGenerating documentation for: {db.name}...')
                    try:
                        # Clear previous messages
                        message_collector.messages = []
                        
                        # Call the documentation generation function
                        queryset = SqlDb.objects.filter(id=db.id)
                        generate_db_documentation(None, mock_request, queryset)
                        
                        # Check if successful
                        has_error = any(
                            msg['level'] == django_messages.ERROR 
                            for msg in message_collector.messages
                        )
                        if not has_error:
                            success_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Generated documentation for {db.name}')
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'✗ Documentation generation had errors for {db.name}')
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
            finally:
                # Restore original messages framework
                django_messages.add_message = original_add_message
                django_messages.success = original_success
                django_messages.error = original_error
                django_messages.warning = original_warning
                django_messages.info = original_info
                
        except Workspace.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Demo workspace (ID=1) not found. Please run load_defaults first.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )