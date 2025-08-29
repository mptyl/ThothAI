# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand
from thoth_core.models import Workspace
import csv
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Export Workspace data to CSV, excluding specific fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='exports',
            help='Output directory for CSV files (default: exports)'
        )

    def handle(self, *args, **options):
        output_dir = options.get('output_dir', 'exports')
        self.stdout.write(self.style.SUCCESS('Starting Workspace CSV export'))
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        csv_path = os.path.join(output_dir, 'workspace.csv')
        
        # Import the excluded fields function
        from thoth_core.utilities.utils import get_workspace_excluded_fields

        # Define fields to export (excluding unwanted fields)
        excluded_fields = get_workspace_excluded_fields()
        
        # Get all model fields
        model_fields = [f.name for f in Workspace._meta.fields if f.name not in excluded_fields]
        m2m_fields = [f.name for f in Workspace._meta.many_to_many]
        
        # Combine all fields
        all_fields = model_fields + m2m_fields
        
        exported_count = 0
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(all_fields)
            
            # Write data
            for workspace in Workspace.objects.all():
                row = []
                
                # Handle regular fields
                for field in model_fields:
                    value = getattr(workspace, field)
                    if field.endswith('_id'):
                        row.append(value)
                    elif hasattr(value, 'pk'):
                        row.append(value.pk)
                    else:
                        row.append(value)
                
                # Handle many-to-many fields
                for m2m_field in m2m_fields:
                    related_objects = getattr(workspace, m2m_field).all()
                    row.append(','.join(str(related.pk) for related in related_objects))
                
                writer.writerow(row)
                exported_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Workspace export completed. Exported {exported_count} workspaces to {csv_path}'
            )
        )
