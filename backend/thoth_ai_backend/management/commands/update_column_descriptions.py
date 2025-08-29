# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

import argparse
from django.core.management.base import BaseCommand, CommandError
from thoth_ai_backend.preprocessing.update_database_columns_direct import update_database_columns_description
from thoth_core.models import Workspace
import logging

# Configure logging for the command
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates database column descriptions for a given workspace ID using data from CSV files.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace_id',
            type=int,
            required=True,
            help='The ID of the workspace for which to update column descriptions.'
        )

    def handle(self, *args, **options):
        workspace_id = options['workspace_id']

        self.stdout.write(self.style.NOTICE(f"Starting column description update for workspace ID: {workspace_id}"))

        try:
            # Check if workspace exists
            if not Workspace.objects.filter(id=workspace_id).exists():
                raise CommandError(f"Workspace with ID {workspace_id} does not exist.")

            # Call the centralized function
            update_database_columns_description(workspace_id=workspace_id)
            
            self.stdout.write(self.style.SUCCESS(f"Successfully updated column descriptions for workspace ID: {workspace_id}"))
            logger.info(f"Successfully updated column descriptions for workspace ID: {workspace_id} via management command.")

        except CommandError as e:
            # CommandError is already styled, so just re-raise or print
            self.stderr.write(self.style.ERROR(str(e)))
            logger.error(f"CommandError for workspace ID {workspace_id}: {str(e)}")
            # Optionally, re-raise if you want the command to exit with a non-zero status for CI/CD
            # raise e 
        except FileNotFoundError as e:
            self.stderr.write(self.style.ERROR(f"File not found during update for workspace ID {workspace_id}: {str(e)}"))
            logger.error(f"FileNotFoundError for workspace ID {workspace_id}: {str(e)}")
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f"Value error during update for workspace ID {workspace_id}: {str(e)}"))
            logger.error(f"ValueError for workspace ID {workspace_id}: {str(e)}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred for workspace ID {workspace_id}: {str(e)}"))
            logger.error(f"Unexpected error for workspace ID {workspace_id}: {str(e)}", exc_info=True)
            # Optionally, re-raise for non-zero exit status
            # raise CommandError(f"An unexpected error occurred: {e}") from e
