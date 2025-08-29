# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand
from django.utils import timezone
from thoth_core.models import SqlTable, SqlDb
import csv
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import SqlTable data from CSV, preserving original IDs'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting SqlTable CSV import'))
        
        csv_path = os.path.join(settings.BASE_DIR, 'setup_csv', 'sqltable.csv')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'SqlTable CSV file not found at {csv_path}'))
            return
        
        imported_count = 0
        updated_count = 0
        error_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    # Estrai l'ID dal CSV
                    model_id = row.get('id')
                    
                    # Ottieni il SqlDb associato
                    sql_db = None
                    if row.get('sql_db'):
                        try:
                            sql_db = SqlDb.objects.get(id=row['sql_db'])
                        except (SqlDb.DoesNotExist, ValueError):
                            try:
                                # Try to get by name
                                sql_db = SqlDb.objects.filter(name=row['sql_db']).first()
                            except Exception:
                                self.stdout.write(self.style.WARNING(
                                    f"SqlDb '{row['sql_db']}' not found for SqlTable '{row.get('name', 'unknown')}'"
                                ))
                                continue  # Skip this row if we don't find the database
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"Missing sql_db reference for SqlTable '{row.get('name', 'unknown')}'"
                        ))
                        continue  # Skip this row if there's no database reference
                    
                    if not model_id:
                        self.stdout.write(self.style.WARNING(f"Missing ID in row, using name and sql_db as key: {row.get('name')}"))
                        # If there's no ID, use name and database as key
                        obj, created = SqlTable.objects.update_or_create(
                            name=row['name'],
                            sql_db=sql_db,
                            defaults={
                                'original_table_name': row.get('original_table_name', row['name']),
                                'table_description': row.get('table_description', ''),
                                'generated_comment': row.get('generated_comment', ''),
                                'schema': row.get('schema', 'public')
                            }
                        )
                        if created:
                            imported_count += 1
                            self.stdout.write(f"Created SqlTable: {obj.name} in {sql_db.name}")
                        else:
                            updated_count += 1
                            self.stdout.write(f"Updated SqlTable: {obj.name} in {sql_db.name}")
                    else:
                        # If there's an ID, try to update the existing object or create a new one with that ID
                        try:
                            obj = SqlTable.objects.get(id=model_id)
                            # Aggiorna i campi
                            obj.name = row['name']
                            obj.original_table_name = row.get('original_table_name', row['name'])
                            obj.sql_db = sql_db
                            obj.table_description = row.get('table_description', '')
                            obj.generated_comment = row.get('generated_comment', '')
                            obj.schema = row.get('schema', 'public')
                            obj.save()
                            updated_count += 1
                            self.stdout.write(f"Updated SqlTable with ID {model_id}: {obj.name} in {sql_db.name}")
                        except SqlTable.DoesNotExist:
                            # Crea un nuovo oggetto con l'ID specificato
                            obj = SqlTable.objects.create(
                                id=model_id,
                                name=row['name'],
                                original_table_name=row.get('original_table_name', row['name']),
                                sql_db=sql_db,
                                table_description=row.get('table_description', ''),
                                generated_comment=row.get('generated_comment', ''),
                                schema=row.get('schema', 'public')
                            )
                            obj.save()
                            imported_count += 1
                            self.stdout.write(f"Created SqlTable with ID {model_id}: {obj.name} in {sql_db.name}")
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"Error processing SqlTable {row.get('name', 'unknown')}: {str(e)}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'SqlTable import completed. Created: {imported_count}, Updated: {updated_count}, Errors: {error_count}'
            )
        )

    def get_defaults_from_row(self, row):
        """Extract default values from CSV row"""
        defaults = {
            'description': row.get('description', ''),
            'generated_comment': row.get('generated_comment', ''),
        }
        
        # Add datetime fields if present
        if 'created_at' in row and row['created_at']:
            defaults['created_at'] = self.parse_datetime(row['created_at'])
        if 'updated_at' in row and row['updated_at']:
            defaults['updated_at'] = self.parse_datetime(row['updated_at'])
            
        return defaults

    def parse_datetime(self, datetime_str):
        """Parse a datetime string to a datetime object"""
        if not datetime_str or datetime_str.lower() in ('null', 'none', ''):
            return None
        
        try:
            from django.utils.dateparse import parse_datetime
            return parse_datetime(datetime_str)
        except Exception:
            self.stdout.write(self.style.WARNING(f"Could not parse datetime: {datetime_str}"))
            return None
