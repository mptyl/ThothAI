# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from thoth_core.models import Workspace, SqlDb, Agent, AiModel, Setting
import csv
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import Workspace data from CSV, preserving original IDs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['local', 'docker'],
            default='local',
            help='Source of CSV files to import (local or docker)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Workspace CSV import'))
        
        source = options.get('source', 'local')
        csv_path = os.path.join(settings.BASE_DIR, 'setup_csv', 'workspace.csv')
        source_specific_path = os.path.join(settings.BASE_DIR, 'setup_csv', source, 'workspace.csv')
        
        if os.path.exists(source_specific_path):
            csv_path = source_specific_path
            self.stdout.write(f'Using source-specific file: {csv_path}')
        else:
            self.stdout.write(f'Using default file: {csv_path}')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'Workspace CSV file not found at {csv_path}'))
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
                    
                    # Ottieni il SqlDb associato se presente - solo per ID
                    sql_db = None
                    if row.get('sql_db'):
                        try:
                            sql_db = SqlDb.objects.get(id=row['sql_db'])
                        except (SqlDb.DoesNotExist, ValueError):
                            self.stdout.write(self.style.WARNING(
                                f"SqlDb with ID '{row['sql_db']}' not found for Workspace '{row.get('name', 'unknown')}'"
                            ))
                    
                    # Ottieni gli agenti associati
                    agents = {}
                    agent_fields = [
                        'kw_sel_agent',
                        'sql_basic_agent', 'sql_advanced_agent', 'sql_expert_agent',
                        'test_gen_agent_1', 'test_gen_agent_2', 'test_exec_agent',
                        'explain_sql_agent', 'ask_human_help_agent'
                    ]
                    
                    for field in agent_fields:
                        if row.get(field):
                            try:
                                agents[field] = Agent.objects.get(id=row[field])
                            except (Agent.DoesNotExist, ValueError):
                                self.stdout.write(self.style.WARNING(
                                    f"Agent with ID '{row[field]}' not found for Workspace '{row.get('name', 'unknown')}' field {field}"
                                ))

                    # Legacy CSV compatibility: map kw_sel_agent_1/2 to kw_sel_agent if present
                    if not agents.get('kw_sel_agent'):
                        legacy_kw1 = row.get('kw_sel_agent_1')
                        legacy_kw2 = row.get('kw_sel_agent_2')
                        chosen_legacy = legacy_kw1 or legacy_kw2
                        if chosen_legacy:
                            try:
                                agents['kw_sel_agent'] = Agent.objects.get(id=chosen_legacy)
                                self.stdout.write("Mapped legacy kw_sel_agent_1/2 to kw_sel_agent")
                            except (Agent.DoesNotExist, ValueError):
                                pass
                    
                    # Handle default_model - support both 'default_model' and legacy 'default_agent' columns
                    default_model = None
                    if row.get('default_model'):
                        try:
                            default_model = AiModel.objects.get(id=row['default_model'])
                        except (AiModel.DoesNotExist, ValueError):
                            self.stdout.write(self.style.WARNING(
                                f"AiModel with ID '{row['default_model']}' not found for Workspace '{row.get('name', 'unknown')}'"
                            ))
                    elif row.get('default_agent'):
                        # Legacy support: extract AiModel from Agent
                        try:
                            agent = Agent.objects.get(id=row['default_agent'])
                            if agent.ai_model:
                                default_model = agent.ai_model
                                self.stdout.write(f"Migrated default_agent '{agent.name}' to default_model '{default_model.name}' for Workspace '{row.get('name', 'unknown')}'")
                        except (Agent.DoesNotExist, ValueError):
                            self.stdout.write(self.style.WARNING(
                                f"Agent with ID '{row['default_agent']}' not found for legacy default_agent field"
                            ))
                    
                    # Get associated settings - only by ID
                    setting = None
                    if row.get('setting'):
                        try:
                            setting = Setting.objects.get(id=row['setting'])
                        except (Setting.DoesNotExist, ValueError):
                            self.stdout.write(self.style.WARNING(
                                f"Setting with ID '{row['setting']}' not found for Workspace '{row.get('name', 'unknown')}'"
                            ))
                    
                    # Note: Excluded datetime fields are no longer parsed from CSV
                    # They will be set to their default values (None or auto-generated)

                    # Gestisci il campo level
                    level = row.get('level', 'BASIC')  # Default to BASIC if not specified
                    
                    # Estrai l'ID dal CSV - richiesto obbligatoriamente
                    if not model_id:
                        self.stdout.write(self.style.WARNING(f"Missing ID for Workspace {row.get('name', 'unknown')}, skipping"))
                        continue
                    
                    # Cerca di aggiornare l'oggetto esistente o creane uno nuovo con quell'ID
                    try:
                        obj = Workspace.objects.get(id=model_id)
                        # Aggiorna i campi
                        obj.name = row['name']
                        obj.level = level
                        obj.description = row.get('description', '')
                        obj.sql_db = sql_db
                        obj.default_model = default_model
                        obj.kw_sel_agent = agents.get('kw_sel_agent')
                        obj.sql_basic_agent = agents.get('sql_basic_agent')
                        obj.sql_advanced_agent = agents.get('sql_advanced_agent')
                        obj.sql_expert_agent = agents.get('sql_expert_agent')
                        obj.test_gen_agent_1 = agents.get('test_gen_agent_1')
                        obj.test_gen_agent_2 = agents.get('test_gen_agent_2')
                        obj.test_exec_agent = agents.get('test_exec_agent')
                        obj.explain_sql_agent = agents.get('explain_sql_agent')
                        obj.ask_human_help_agent = agents.get('ask_human_help_agent')
                        obj.setting = setting

                        # Reset excluded fields to default values
                        obj.preprocessing_status = Workspace.PreprocessingStatus.IDLE
                        obj.task_id = None
                        obj.last_preprocess_log = None
                        obj.preprocessing_start_time = None
                        obj.preprocessing_end_time = None

                        obj.table_comment_status = Workspace.PreprocessingStatus.IDLE
                        obj.table_comment_task_id = None
                        obj.table_comment_log = None
                        obj.table_comment_start_time = None
                        obj.table_comment_end_time = None

                        obj.column_comment_status = Workspace.PreprocessingStatus.IDLE
                        obj.column_comment_task_id = None
                        obj.column_comment_log = None
                        obj.column_comment_start_time = None
                        obj.column_comment_end_time = None

                        # Reset timestamp fields
                        obj.last_preprocess = None
                        obj.last_evidence_load = None
                        obj.last_sql_loaded = None
                        # Note: created_at and updated_at are handled automatically by Django

                        obj.save()
                        updated_count += 1
                        self.stdout.write(f"Updated Workspace with ID {model_id}: {obj.name}")

                        # Handle many-to-many relationships for update case
                        if 'users' in row and row['users']:
                            try:
                                user_ids = [int(uid.strip()) for uid in row['users'].split(',') if uid.strip()]
                                existing_users = User.objects.filter(id__in=user_ids)
                                obj.users.set(existing_users)
                                self.stdout.write(f"Set {len(existing_users)} users for workspace {obj.name}")
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(
                                    f"Error setting users for workspace {obj.name}: {str(e)}"
                                ))

                        if 'default_workspace' in row and row['default_workspace']:
                            try:
                                default_user_ids = [int(uid.strip()) for uid in row['default_workspace'].split(',') if uid.strip()]
                                existing_default_users = User.objects.filter(id__in=default_user_ids)
                                obj.default_workspace.set(existing_default_users)
                                self.stdout.write(f"Set {len(existing_default_users)} default users for workspace {obj.name}")
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(
                                    f"Error setting default users for workspace {obj.name}: {str(e)}"
                                ))

                    except Workspace.DoesNotExist:
                        # Crea un nuovo oggetto con l'ID specificato
                        obj = Workspace.objects.create(
                            id=model_id,
                            name=row['name'],
                            level=level,
                            description=row.get('description', ''),
                            sql_db=sql_db,
                            default_model=default_model,
                            kw_sel_agent=agents.get('kw_sel_agent'),
                            sql_basic_agent=agents.get('sql_basic_agent'),
                            sql_advanced_agent=agents.get('sql_advanced_agent'),
                            sql_expert_agent=agents.get('sql_expert_agent'),
                            test_gen_agent_1=agents.get('test_gen_agent_1'),
                            test_gen_agent_2=agents.get('test_gen_agent_2'),
                            test_exec_agent=agents.get('test_exec_agent'),
                            explain_sql_agent=agents.get('explain_sql_agent'),
                            ask_human_help_agent=agents.get('ask_human_help_agent'),
                            setting=setting
                            # Note: Excluded fields will be set to their default values automatically
                        )
                        imported_count += 1
                        self.stdout.write(f"Created Workspace with ID {model_id}: {obj.name}")

                    # Handle many-to-many relationships for both update and create cases
                    if 'users' in row and row['users']:
                        try:
                            user_ids = [int(uid.strip()) for uid in row['users'].split(',') if uid.strip()]
                            existing_users = User.objects.filter(id__in=user_ids)
                            obj.users.set(existing_users)
                            self.stdout.write(f"Set {len(existing_users)} users for workspace {obj.name}")
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(
                                f"Error setting users for workspace {obj.name}: {str(e)}"
                            ))

                    if 'default_workspace' in row and row['default_workspace']:
                        try:
                            default_user_ids = [int(uid.strip()) for uid in row['default_workspace'].split(',') if uid.strip()]
                            existing_default_users = User.objects.filter(id__in=default_user_ids)
                            obj.default_workspace.set(existing_default_users)
                            self.stdout.write(f"Set {len(existing_default_users)} default users for workspace {obj.name}")
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(
                                f"Error setting default users for workspace {obj.name}: {str(e)}"
                            ))

                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f"Error processing row {row}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f'Import completed. Imported: {imported_count}, Updated: {updated_count}, Errors: {error_count}'))

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
