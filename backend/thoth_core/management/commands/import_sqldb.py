# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand
from django.utils import timezone
from thoth_core.models import SqlDb, VectorDb
import csv
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import SqlDb data from CSV, preserving original IDs'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting SqlDb CSV import'))
        
        csv_path = os.path.join(settings.BASE_DIR, 'setup_csv', 'sqldb.csv')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'SqlDb CSV file not found at {csv_path}'))
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
                    
                    # Ottieni il VectorDb associato se presente
                    vector_db = None
                    if row.get('vector_db'):
                        try:
                            vector_db = VectorDb.objects.get(id=row['vector_db'])
                        except (VectorDb.DoesNotExist, ValueError):
                            try:
                                # Try to get by name
                                vector_db = VectorDb.objects.filter(name=row['vector_db']).first()
                            except Exception:
                                self.stdout.write(self.style.WARNING(
                                    f"VectorDb '{row['vector_db']}' not found for SqlDb '{row.get('name', 'unknown')}'"
                                ))
                    
                    # Prepare values for boolean fields
                    is_active = self.parse_boolean(row.get('is_active', 'True'))
                    
                    if not model_id:
                        self.stdout.write(self.style.WARNING(f"Missing ID in row, using name as key: {row.get('name')}"))
                        # If there's no ID, use name as key
                        # Handle db_port field
                        db_port = None
                        if row.get('db_port') and row.get('db_port').strip():
                            try:
                                db_port = int(row.get('db_port'))
                            except (ValueError, TypeError):
                                self.stdout.write(self.style.WARNING(f"Invalid db_port value '{row.get('db_port')}' for SqlDb '{row.get('name')}', setting to None"))
                                db_port = None

                        obj, created = SqlDb.objects.update_or_create(
                            name=row['name'],
                            defaults={
                                'db_host': row.get('db_host', ''),
                                'db_port': db_port,
                                'user_name': row.get('user_name', ''),
                                'password': row.get('password', ''),
                                'db_name': row.get('db_name', ''),
                                'schema': row.get('schema', ''),
                                'db_type': row.get('db_type', 'POSTGRES'),
                                'vector_db': vector_db,
                            }
                        )
                        if created:
                            imported_count += 1
                            self.stdout.write(f"Created SqlDb: {obj.name}")
                        else:
                            updated_count += 1
                            self.stdout.write(f"Updated SqlDb: {obj.name}")
                    else:
                        # If there's an ID, try to update the existing object or create a new one with that ID
                        try:
                            obj = SqlDb.objects.get(id=model_id)
                            # Aggiorna i campi
                            obj.name = row['name']
                            obj.db_host = row.get('db_host', '')

                            # Handle db_port field
                            if row.get('db_port') and row.get('db_port').strip():
                                try:
                                    obj.db_port = int(row.get('db_port'))
                                except (ValueError, TypeError):
                                    self.stdout.write(self.style.WARNING(f"Invalid db_port value '{row.get('db_port')}' for SqlDb '{row.get('name')}', setting to None"))
                                    obj.db_port = None
                            else:
                                obj.db_port = None

                            obj.user_name = row.get('user_name', '')
                            obj.password = row.get('password', '')
                            obj.db_name = row.get('db_name', '')
                            obj.schema = row.get('schema', '')
                            obj.db_type = row.get('db_type', 'POSTGRES')
                            obj.vector_db = vector_db
                            obj.save()
                            updated_count += 1
                            self.stdout.write(f"Updated SqlDb with ID {model_id}: {obj.name}")
                        except SqlDb.DoesNotExist:
                            # Handle db_port field for new object
                            db_port = None
                            if row.get('db_port') and row.get('db_port').strip():
                                try:
                                    db_port = int(row.get('db_port'))
                                except (ValueError, TypeError):
                                    self.stdout.write(self.style.WARNING(f"Invalid db_port value '{row.get('db_port')}' for SqlDb '{row.get('name')}', setting to None"))
                                    db_port = None

                            # Crea un nuovo oggetto con l'ID specificato
                            obj = SqlDb.objects.create(
                                id=model_id,
                                name=row['name'],
                                db_host=row.get('db_host', ''),
                                db_port=db_port,
                                user_name=row.get('user_name', ''),
                                password=row.get('password', ''),
                                db_name=row.get('db_name', ''),
                                schema=row.get('schema', ''),
                                db_type=row.get('db_type', 'POSTGRES'),
                                vector_db=vector_db,
                            )
                            imported_count += 1
                            self.stdout.write(f"Created SqlDb with ID {model_id}: {obj.name}")
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"Error processing SqlDb {row.get('name', 'unknown')}: {str(e)}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'SqlDb import completed. Created: {imported_count}, Updated: {updated_count}, Errors: {error_count}'
            )
        )

    def parse_boolean(self, value):
        """Parse a string to a boolean value"""
        if isinstance(value, bool):
            return value
        if not value:
            return False
        return value.lower() in ('true', 't', 'yes', 'y', '1')

    def get_defaults_from_row(self, row):
        """Extract default values from CSV row"""
        defaults = {
            'db_type': row.get('db_type', 'POSTGRESQL'),
            'host': row.get('host', 'localhost'),
            'username': row.get('username', ''),
            'password': row.get('password', ''),
            'database': row.get('database', ''),
            'schema': row.get('schema', 'public'),
        }
        
        # Handle port field
        if 'port' in row and row['port']:
            try:
                defaults['port'] = int(row['port'])
            except (ValueError, TypeError):
                defaults['port'] = 5432  # Default PostgreSQL port
        else:
            defaults['port'] = 5432
        
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
