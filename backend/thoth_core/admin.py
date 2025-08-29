# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

from .admin_models.admin_basic_aimodel import *
from .admin_models.admin_aimodel import *
from .admin_models.admin_sqldb import *
from .admin_models.admin_sqltable import *
from .admin_models.admin_sqlcolumn import *
from .admin_models.admin_relationship import *
from .admin_models.admin_vectordb import *
from .admin_models.admin_workspace import *
from .admin_models.admin_setting import *
from .admin_models.admin_agent import *
from .admin_models.admin_groupprofile import *
from .admin_models.admin_thothlog import *

# Shared helper functions (e.g. validate_fk_fields) can remain here if used by multiple admins

def validate_fk_fields(columns, request=None):
    """
    Validates the format of fk_field for the given columns.
    Returns a tuple of (error_count, success_count, error_messages, total_checked)
    """
    from .models import SqlTable, SqlColumn
    
    error_count = 0
    success_count = 0
    error_messages = []
    total_checked = 0
    
    for column in columns:
        # Skip empty fk_field values without counting them
        if not column.fk_field or column.fk_field.strip() == '':
            continue
            
        # Increment the counter for columns with FK values
        total_checked += 1
        
        # Get the SQL database of the table this column belongs to
        sql_db = column.sql_table.sql_db
        
        # Parse references (either a single reference or comma-separated list)
        references = [ref.strip() for ref in column.fk_field.split(',')]
        column_has_error = False
        
        for reference in references:
            # Check format: tablename.columnname
            parts = reference.split('.')
            if len(parts) != 2:
                error_msg = (
                    f"Invalid format in column '{column.original_column_name}' of table '{column.sql_table.name}': "
                    f"'{reference}' should be in format 'tablename.columnname'"
                )
                error_messages.append(error_msg)
                column_has_error = True
                continue
                
            table_name, column_name = parts
            
            # Check if the referenced table exists in the same database
            try:
                ref_table = SqlTable.objects.get(name=table_name, sql_db=sql_db)
            except SqlTable.DoesNotExist:
                error_msg = (
                    f"Invalid reference in column '{column.original_column_name}' of table '{column.sql_table.name}': "
                    f"Table '{table_name}' does not exist in database '{sql_db.name}'"
                )
                error_messages.append(error_msg)
                column_has_error = True
                continue
                
            # Check if the referenced column exists in the referenced table
            if not SqlColumn.objects.filter(sql_table=ref_table, original_column_name=column_name).exists():
                error_msg = (
                    f"Invalid reference in column '{column.original_column_name}' of table '{column.sql_table.name}': "
                    f"Column '{column_name}' does not exist in table '{table_name}'"
                )
                error_messages.append(error_msg)
                column_has_error = True
                continue
        
        # Count errors per column, not per reference
        if column_has_error:
            error_count += 1
        else:
            success_count += 1
    
    return error_count, success_count, error_messages, total_checked