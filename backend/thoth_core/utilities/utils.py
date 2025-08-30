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

import csv
import os

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.core.files.storage import default_storage
from django.conf import settings
from django.db import transaction
from django.db.models import ForeignKey, ManyToManyField, OneToOneField, DateTimeField


def get_workspace_excluded_fields():
    """
    Get the list of fields to exclude when importing/exporting Workspace objects.
    These fields represent transient state and should not be imported/exported.

    Returns:
        set: Set of field names to exclude
    """
    return {
        # Comment Generation Fields
        'table_comment_status',
        'table_comment_task_id',
        'table_comment_log',
        'table_comment_start_time',
        'table_comment_end_time',
        'column_comment_status',
        'column_comment_task_id',
        'column_comment_log',
        'column_comment_start_time',
        'column_comment_end_time',

        # Preprocessing Fields
        'preprocessing_status',
        'task_id',
        'last_preprocess_log',
        'preprocessing_start_time',
        'preprocessing_end_time',

        # All DateTimeField Fields (temporal data)
        'last_preprocess',
        'last_evidence_load',
        'last_sql_loaded',
        'created_at',
        'updated_at',
        # Legacy removed fields (to make import robust across CSVs)
        'kw_sel_agent_1',
        'kw_sel_agent_2',
    }


def get_exports_directory():
    """
    Determine the directory for import/export admin actions.
    Uses the IO_DIR environment variable if present, otherwise 'exports'.
    
    Returns:
        str: The directory path for import/export
    """
    return os.getenv('IO_DIR', 'exports')


def get_docker_friendly_error_message(error):
    """
    Convert system errors into user-friendly messages for Docker.
    
    Args:
        error: The caught OSError exception
        
    Returns:
        str: User-understandable error message
    """
    error_str = str(error).lower()
    
    if "permission denied" in error_str:
        return (
            "Docker volume permissions issue. The exports directory is not writable. "
            "Check that the Docker volume is properly mounted with write permissions. "
            "Try: 'chmod 755 ./exports' on the host system."
        )
    elif "read-only file system" in error_str:
        return (
            "Docker volume not properly mounted as writable. "
            "Check your docker-compose.yml configuration. "
            "The exports volume should be mounted as: './exports:/app/exports:rw'"
        )
    elif "no space left" in error_str:
        return (
            "Insufficient disk space on Docker host. "
            "Free up space on the host system or check Docker volume configuration."
        )
    elif "no such file or directory" in error_str:
        return (
            "Docker volume mount path issue. "
            "Ensure the exports directory exists on the host system: 'mkdir -p ./exports'"
        )
    else:
        return f"File system error: {str(error)}. Check Docker volume configuration and permissions."


def ensure_exports_directory():
    """
    Verify and create the exports directory with complete error handling for Docker.
    
    Returns:
        tuple: (directory_path, error_message) - error_message is None if everything is ok
    """
    io_dir = get_exports_directory()
    
    try:
        # Check if the directory exists
        if os.path.exists(io_dir):
            # Verify write permissions
            if not os.access(io_dir, os.W_OK):
                raise PermissionError(f"No write permission for directory: {io_dir}")
        else:
            # Create the directory
            os.makedirs(io_dir, exist_ok=True)
            
        # Write test to verify everything works
        test_file = os.path.join(io_dir, '.write_test_temp')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            raise OSError(f"Cannot write to directory {io_dir}: {str(e)}")
            
        return io_dir, None
        
    except (OSError, PermissionError) as e:
        error_message = get_docker_friendly_error_message(e)
        return None, error_message


def export_selected_tables_to_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="selected_tables.csv"'

    writer = csv.writer(response)
    writer.writerow(['database', 'name', 'description', 'generated_comment'])

    for table in queryset:
        writer.writerow([
            table.sql_db.id,
            table.name,
            table.description,
            table.generated_comment
        ])

    return response

def export_selected_columns_to_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="selected_columns.csv"'

    writer = csv.writer(response)
    writer.writerow(['Table', 'Column Name', 'Data Type', 'Original Comment', 'Generated Comment', 'Value Description'])

    for column in queryset:
        writer.writerow([
            column.sql_table.id,
            column.original_column_name,
            column.data_format,
            column.column_description,
            column.generated_comment,
            column.value_description,
            column.pk_field,
            column.fk_field
        ])

    return response



def export_csv(modeladmin, request, queryset):
    if not request.user.is_staff:
        raise PermissionDenied

    # Use enhanced directory validation
    io_dir, error_message = ensure_exports_directory()
    if error_message:
        messages.error(request, f"Export failed: {error_message}")
        model = queryset.model
        return HttpResponseRedirect(reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist'))

    model = queryset.model
    model_name = model.__name__.lower()
    # Special case for User model to match import expectations
    if model_name == 'user':
        model_name = 'users'
    # Special case for Group model to match import expectations
    if model_name == 'group':
        model_name = 'groups'
    file_name = f"{model_name}.csv"
    file_path = os.path.join(io_dir, file_name)

    # Get excluded fields for Workspace model
    excluded_fields = set()
    if model_name == 'workspace':
        excluded_fields = get_workspace_excluded_fields()

    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        fields = [f.name for f in model._meta.fields if f.name not in excluded_fields]
        m2m_fields = [f.name for f in model._meta.many_to_many]
        writer.writerow(fields + m2m_fields)

        for obj in queryset:
            row = []
            for field in fields:
                value = getattr(obj, field)
                if field.endswith('_id'):
                    row.append(value)
                elif hasattr(value, 'pk'):
                    row.append(value.pk)
                else:
                    row.append(value)
            for m2m_field in m2m_fields:
                related_objects = getattr(obj, m2m_field).all()
                row.append(','.join(str(related.pk) for related in related_objects))
            writer.writerow(row)

    # Prepare the HTTP response
    with open(file_path, 'rb') as file:
        response = HttpResponse(file.read(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    messages.success(request, f"CSV export for {model_name} completed successfully. The file is available in the exports directory at {io_dir}/{file_name}.")
    return HttpResponseRedirect(reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist'))


def import_csv(modeladmin, request, queryset):
    model_name = modeladmin.model.__name__.lower()
    # Special case for User model to match export expectations
    if model_name == 'user':
        model_name = 'users'
    # Special case for Group model to match export expectations
    if model_name == 'group':
        model_name = 'groups'
    
    # Use enhanced directory validation
    io_dir, error_message = ensure_exports_directory()
    if error_message:
        modeladmin.message_user(request, f"Import failed: {error_message}", level='error')
        return
        
    file_path = os.path.join(io_dir, f"{model_name}.csv")

    if not default_storage.exists(file_path):
        modeladmin.message_user(request, f"CSV file for {model_name} not found in exports directory '{io_dir}'. Make sure to export the data first or check Docker volume mounting.", level='error')
        return

    Model = modeladmin.model

    # Get excluded fields for Workspace model
    excluded_fields = set()
    if model_name == 'workspace':
        excluded_fields = get_workspace_excluded_fields()

    with default_storage.open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        success_count = 0
        error_count = 0
        for row in reader:
            try:
                with transaction.atomic():
                    pk_field = Model._meta.pk.name
                    instance_data = {}
                    m2m_data = {}

                    for field_name, value in row.items():
                        # Skip excluded fields for Workspace
                        if field_name in excluded_fields:
                            continue

                        try:
                            field = Model._meta.get_field(field_name)
                            if isinstance(field, (ForeignKey, OneToOneField)):
                                if value.strip():
                                    instance_data[field_name] = field.related_model.objects.get(pk=value.strip())
                            elif isinstance(field, ManyToManyField):
                                if value.strip():
                                    m2m_data[field_name] = [int(id.strip()) for id in value.split(',') if id.strip()]
                            else:
                                instance_data[field_name] = value
                        except Exception:
                            # Skip fields that don't exist in the model (e.g., removed fields)
                            continue

                    pk_value = row.get(pk_field, '').strip()
                    if pk_value:
                        instance, created = Model.objects.update_or_create(
                            **{pk_field: pk_value},
                            defaults=instance_data
                        )
                    else:
                        instance = Model.objects.create(**{k: v for k, v in instance_data.items() if k != 'id' or v})

                    # Set default values for excluded fields if this is a Workspace
                    if model_name == 'workspace':
                        from thoth_core.models import Workspace
                        # Reset status fields to default values
                        instance.preprocessing_status = Workspace.PreprocessingStatus.IDLE
                        instance.task_id = None
                        instance.last_preprocess_log = None
                        instance.preprocessing_start_time = None
                        instance.preprocessing_end_time = None

                        instance.table_comment_status = Workspace.PreprocessingStatus.IDLE
                        instance.table_comment_task_id = None
                        instance.table_comment_log = None
                        instance.table_comment_start_time = None
                        instance.table_comment_end_time = None

                        instance.column_comment_status = Workspace.PreprocessingStatus.IDLE
                        instance.column_comment_task_id = None
                        instance.column_comment_log = None
                        instance.column_comment_start_time = None
                        instance.column_comment_end_time = None

                        # Reset timestamp fields
                        instance.last_preprocess = None
                        instance.last_evidence_load = None
                        instance.last_sql_loaded = None
                        # Note: created_at and updated_at are handled automatically by Django

                        instance.save()

                    for field_name, ids in m2m_data.items():
                        getattr(instance, field_name).set(ids)

                success_count += 1
            except Exception as e:
                error_count += 1
                modeladmin.message_user(request, f"Error on row {reader.line_num}: {str(e)}", level='error')

    modeladmin.message_user(request, f"CSV import from exports directory completed. {success_count} rows imported successfully, {error_count} rows failed.")

def export_db_structure_to_csv(modeladmin, request, queryset):
    """
    Export selected databases and all their related tables, columns, and relationships to CSV files
    using the standard export format and location with enhanced Docker error handling
    """
    from thoth_core.models import SqlTable, SqlColumn, Relationship
    import csv
    import os
    from django.conf import settings
    
    # Use enhanced directory validation
    io_dir, error_message = ensure_exports_directory()
    if error_message:
        messages.error(request, f"Database structure export failed: {error_message}")
        return
        
    export_dir = os.path.join(settings.BASE_DIR, io_dir)
    
    # Additional check for the full path (BASE_DIR + io_dir)
    try:
        os.makedirs(export_dir, exist_ok=True)
        # Test write access to the full path
        test_file = os.path.join(export_dir, '.write_test_temp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
    except (OSError, PermissionError) as e:
        docker_error = get_docker_friendly_error_message(e)
        messages.error(request, f"Database structure export failed: {docker_error}")
        return
    
    # Track what was exported
    exported_dbs = []
    exported_tables_count = 0
    exported_columns_count = 0
    exported_relationships_count = 0
    
    for db in queryset:
        exported_dbs.append(db.name)
        
        # Export tables
        tables = SqlTable.objects.filter(sql_db=db)
        exported_tables_count += tables.count()
        tables_file = os.path.join(export_dir, f"{db.name}_tables.csv")
        with open(tables_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name',  'description', 'generated_comment', 'sql_db'])
            for table in tables:
                writer.writerow([
                    table.id,
                    table.name,
                    table.description,
                    table.generated_comment,
                    db.id  # Use ID instead of name for foreign key references
                ])
        
        # Export columns
        columns = SqlColumn.objects.filter(sql_table__sql_db=db)
        exported_columns_count += columns.count()
        columns_file = os.path.join(export_dir, f"{db.name}_columns.csv")
        with open(columns_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'original_column_name', 'column_name', 'data_format', 
                'column_description', 'generated_comment', 'value_description',
                'sql_table_id', 'pk_field', 'fk_field'
            ])
            for column in columns:
                writer.writerow([
                    column.id,
                    column.original_column_name,
                    column.column_name,
                    column.data_format,
                    column.column_description,
                    column.generated_comment,
                    column.value_description,
                    column.sql_table.id,  # Use ID instead of name
                    column.pk_field,
                    column.fk_field
                ])
        
        # Export relationships
        relationships = Relationship.objects.filter(
            source_table__sql_db=db
        ) | Relationship.objects.filter(
            target_table__sql_db=db
        )
        exported_relationships_count += relationships.count()
        relationships_file = os.path.join(export_dir, f"{db.name}_relationships.csv")
        with open(relationships_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'source_table', 'source_column', 'target_table', 
                'target_column'
            ])
            for rel in relationships:
                writer.writerow([
                    rel.id,
                    rel.source_table.id,
                    rel.source_column.id,
                    rel.target_table.id,
                    rel.target_column.id,
                ])
    
    # Also export the database itself
    db_file = os.path.join(export_dir, 'selected_dbs.csv')
    with open(db_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'id', 'name', 'db_host', 'db_type', 'db_name', 'db_port', 'schema',
            'user_name', 'password', 'db_mode', 'vector_db', 'language', 'scope', 'scope_json', 'directives', 'erd'
        ])
        for db in queryset:
            writer.writerow([
                db.id,
                db.name, 
                db.db_host,
                db.db_type,
                db.db_name,
                db.db_port,
                db.schema,
                db.user_name,
                db.password,
                db.db_mode,
                db.vector_db.id if db.vector_db else '',
                db.language,
                db.scope,
                db.scope_json,
                db.directives,
                db.erd,
            ])
    
    modeladmin.message_user(
        request, 
        f"Successfully exported {len(exported_dbs)} database(s) ({', '.join(exported_dbs)}) with {exported_tables_count} tables, "
        f"{exported_columns_count} columns, and {exported_relationships_count} relationships to {export_dir}"
    )

export_db_structure_to_csv.short_description = "Export database structure to CSV files"


def initialize_database_plugins():
    """
    Initialize available database plugins by importing the plugins module
    and discovering which databases have their dependencies installed.
    
    Returns:
        Dict[str, bool]: Dictionary mapping database names to availability status
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from thoth_dbmanager import get_available_databases
        
        # Import plugins module to trigger auto-registration of all plugins
        import thoth_dbmanager.plugins
        logger.info("Database plugins module imported successfully")
        
        # Get available databases based on installed dependencies
        available_databases = get_available_databases()
        
        # Log available plugins
        available_list = [db for db, available in available_databases.items() if available]
        unavailable_list = [db for db, available in available_databases.items() if not available]
        
        if available_list:
            logger.info(f"Available database plugins: {', '.join(available_list)}")
        if unavailable_list:
            logger.info(f"Unavailable database plugins (missing dependencies): {', '.join(unavailable_list)}")
            
        return available_databases
        
    except Exception as e:
        logger.error(f"Error initializing database plugins: {str(e)}")
        return {}
