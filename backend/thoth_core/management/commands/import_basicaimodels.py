# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.core.management.base import BaseCommand
from django.utils import timezone
from thoth_core.models import BasicAiModel
import csv
import os
from django.conf import settings
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import BasicAiModel data from CSV, preserving original IDs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['local', 'docker'],
            default='local',
            help='Source of CSV files to import (local or docker)'
        )

    def handle(self, *args, **options):
        source = options.get('source', 'local')
        self.stdout.write(self.style.SUCCESS('Starting BasicAiModel CSV import'))
        
        csv_path = os.path.join(settings.BASE_DIR, 'setup_csv', 'basicaimodel.csv')
        source_specific_path = os.path.join(settings.BASE_DIR, 'setup_csv', source, 'basicaimodel.csv')
        
        if os.path.exists(source_specific_path):
            csv_path = source_specific_path
            self.stdout.write(f'Using source-specific file: {csv_path}')
        else:
            self.stdout.write(f'Using default file: {csv_path}')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'BasicAiModel CSV file not found at {csv_path}'))
            return
        
        # Leggi prima tutti i dati dal CSV
        csv_data = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                csv_data.append(row)
        
        if not csv_data:
            self.stdout.write(self.style.WARNING('CSV file is empty. No records to import.'))
            return
        
        # Usa una transazione per garantire l'atomicità dell'operazione
        with transaction.atomic():
            # Cancella tutti i record esistenti
            deleted_count = BasicAiModel.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} existing BasicAiModel records'))
            
            # Importa i nuovi record mantenendo gli ID originali
            imported_count = 0
            error_count = 0
            
            for row in csv_data:
                try:
                    # Estrai l'ID dal CSV
                    model_id = row.get('id')
                    if not model_id:
                        self.stdout.write(self.style.ERROR(f"Missing ID in row: {row}"))
                        error_count += 1
                        continue
                    
                    # Crea un nuovo oggetto BasicAiModel con l'ID specificato
                    model = BasicAiModel(
                        id=model_id,
                        name=row.get('name', ''),
                        description=row.get('description', ''),
                        provider=row.get('provider', 'ANTHROPIC')
                    )
                    
                    # Gestisci i campi datetime se presenti
                    if 'created_at' in row and row['created_at']:
                        model.created_at = self.parse_datetime(row['created_at'])
                    if 'updated_at' in row and row['updated_at']:
                        model.updated_at = self.parse_datetime(row['updated_at'])
                    
                    # Salva il modello
                    model.save()
                    imported_count += 1
                    self.stdout.write(f"Imported BasicAiModel: {model.name} (ID: {model.id})")
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"Error importing BasicAiModel {row.get('name', 'unknown')}: {str(e)}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'BasicAiModel import completed. Imported: {imported_count}, Errors: {error_count}'
            )
        )

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
