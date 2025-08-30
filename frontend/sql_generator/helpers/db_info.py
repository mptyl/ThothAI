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

import logging
import json
import pandas as pd

from typing import Dict, List, Any

from django_api.django_api_using_apikey import get_db_tables, get_table_columns

def get_db_schema(db_id: str, db_schema:str) -> Dict[str, Dict[str, Any]]:
    """
    Retrieves the complete schema of the database with detailed column information and table descriptions.
    
    The returned structure separates table info from columns:
    {
        "table_name": {
            "table_description": str,
            "columns": {
                "column_name": {
                    "original_column_name": str,
                    "data_format": str,
                    "column_description": str,
                    "value_description": str,
                    "pk_field": str,
                    "fk_field": str
                }
            }
        }
    }
    """
    from helpers.dual_logger import log_error, log_info
    
    if not db_id:
        error_msg = "get_db_schema called with empty db_id"
        log_error(error_msg)
        raise ValueError(error_msg)
    
    try:
        schema = {}
        table_list = get_db_tables(db_id)
        
        if not table_list:
            error_msg = f"No tables found for database {db_id}"
            log_error(error_msg)
            raise ValueError(error_msg)
        
        for table in table_list:
            table_name = table["name"]
            table_description = table.get("description", "")
            table_comment = table.get("generated_comment", "")
            
            # Initialize table with separate table_description and columns
            schema[table_name] = {
                "table_description": table_description,
                "columns": {}
            }
            
            # Get columns information
            try:
                columns = get_table_columns(db_id, table_name)
                for column in columns:
                    original_name = column["original_column_name"]
                    
                    # Handle pk_field: convert to empty string if 0/False, ensure it's treated as boolean indicator
                    pk_field = column.get("pk_field", "")
                    if pk_field and pk_field != "0" and pk_field != 0 and pk_field != False:
                        # If it's a truthy value, keep it as string representation
                        pk_field = str(pk_field)
                    else:
                        pk_field = ""
                    
                    # Handle fk_field similarly - keep as string with table.column format
                    fk_field = column.get("fk_field", "")
                    if fk_field and fk_field != "0" and fk_field != 0 and fk_field != False:
                        # Keep FK field as string (should be in format "table.column" or "table1.column1,table2.column2")
                        fk_field = str(fk_field).strip()
                    else:
                        fk_field = ""
                    
                    # Create standardized column info
                    column_info = {
                        "original_column_name": original_name,
                        "data_format": column.get("data_format", "VARCHAR"),
                        "column_description": column.get("column_description", ""),
                        "value_description": column.get("value_description", ""),
                        "pk_field": pk_field,
                        "fk_field": fk_field
                    }
                    
                    # Store column info in columns dict
                    schema[table_name]["columns"][original_name] = column_info
                    
            except Exception as e:
                error_details = {
                    "db_id": db_id,
                    "table_name": table_name,
                    "error": str(e)
                }
                log_error(f"Error getting columns for table: {json.dumps(error_details)}")
                # Continue with other tables instead of failing completely
                continue
        
        if not schema:
            error_msg = f"Failed to retrieve schema for any tables in database {db_id}"
            log_error(error_msg)
            raise ValueError(error_msg)
        
        log_info(f"Successfully retrieved schema for {len(schema)} tables from database {db_id}")
        return schema
        
    except Exception as e:
        error_details = {
            "db_id": db_id,
            "db_schema": db_schema,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        log_error(f"Critical error in get_db_schema: {json.dumps(error_details)}")
        raise

def load_tables_description(
    db_name: str, use_value_description: bool
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Loads table descriptions from CSV files in the database directory.

    Args:
        db_name (str): The path to the database directory.
        use_value_description (bool): Whether to include value descriptions.

    Returns:
        Dict[str, Dict[str, Dict[str, str]]]: A dictionary containing table descriptions.
    """
    table_description = {}
    table_list = get_db_tables(db_name)
    for table in table_list:
        table_name = table["name"].lower().strip()
        table_description[table_name] = {}
        could_read = False
        try:
            table_description_df = get_table_columns(db_name, table_name)
            for row in table_description_df:
                column_name = row["original_column_name"]
                expanded_column_name = (
                    row.get("column_name", "").strip()
                    if row.get("column_name")
                    not in (None, "", "nan", "NaN", "null", "NULL")
                    else ""
                )
                column_description = (
                    row.get("column_description", "")
                    .replace("\n", " ")
                    .replace("commonsense evidence:", "")
                    .strip()
                    if pd.notna(row.get("column_description", ""))
                    else ""
                )
                value_description = ""
                if use_value_description and row.get("value_description") not in (
                    None,
                    "",
                    "nan",
                    "NaN",
                    "null",
                    "NULL",
                ):
                    value_description = (
                        row["value_description"]
                        .replace("\n", " ")
                        .replace("commonsense evidence:", "")
                        .strip()
                    )
                    if value_description.lower().startswith("not useful"):
                        value_description = value_description[10:].strip()

                table_description[table_name][column_name.lower().strip()] = {
                    "original_column_name": column_name,
                    "column_name": expanded_column_name,
                    "column_description": column_description,
                    "value_description": value_description,
                }
            logging.info(f"Loaded descriptions from {db_name}")
            could_read = True
            break
        except Exception:
            continue
    if not could_read:
        logging.warning(f"Could not read descriptions from {db_name}")
    return table_description

def columns_select(
    tentative_schema: Dict[str, Dict[str, Dict[str, Any]]],
    similar_entities: Dict[str, Dict[str, List[str]]],
    similar_columns: Dict[str, Dict[str, Dict[str, str]]]
) -> Dict[str, Dict[str, Any]]:
    """
    Creates a filtered schema containing only tables with columns that are either
    in similar_entities or similar_columns, including their primary and foreign keys.
    For columns in similar_entities, adds their example values under VALUE EXAMPLES.

    Args:
        db_name (str): The database name
        similar_entities (Dict[str, Dict[str, List[str]]]): Table->column->list of similar entities
        similar_columns (Dict[str, Dict[str, Dict[str, str]]]): Table->column->attribute:value mapping

    Returns:
        Dict[str, Dict[str, Any]]: Filtered schema with selected tables and columns
    """
    # Get the complete schema
    filtered_schema: Dict[str, Dict[str, Any]] = {}

    # First pass: identify tables with matching columns
    tables_to_include = set()
    for table_name, table_info in tentative_schema.items():
        # Check if table has any columns in similar_entities
        if table_name in similar_entities:
            for col_name in similar_entities[table_name]:
                if col_name in table_info["columns"]:
                    tables_to_include.add(table_name)
                    break

        # Check if table has any columns in similar_columns
        if table_name in similar_columns:
            for col_name in similar_columns[table_name]:
                if col_name in table_info["columns"]:
                    tables_to_include.add(table_name)
                    break

    # Second pass: build filtered schema with required columns
    for table_name in tables_to_include:
        table_info = tentative_schema[table_name]
        filtered_schema[table_name] = {"columns": {}}
        
        # Add columns that are in similar_entities or similar_columns
        columns_to_include = set()
        
        # Add columns from similar_entities
        if table_name in similar_entities:
            columns_to_include.update(similar_entities[table_name].keys())
            
        # Add columns from similar_columns
        if table_name in similar_columns:
            columns_to_include.update(similar_columns[table_name].keys())
            
        # Add primary key columns
        for col_name, col_info in table_info["columns"].items():
            if col_info["pk_field"]:
                columns_to_include.add(col_name)
                
        # Add foreign key columns
        for col_name, col_info in table_info["columns"].items():
            if col_info["fk_field"]:
                columns_to_include.add(col_name)
        
        # Build final columns dict
        for col_name in columns_to_include:
            if col_name in table_info["columns"]:
                # Copy original column info
                filtered_schema[table_name]["columns"][col_name] = table_info["columns"][col_name].copy()
                
                # Add VALUE EXAMPLES if column is in similar_entities
                if (table_name in similar_entities and 
                    col_name in similar_entities[table_name]):
                    filtered_schema[table_name]["columns"][col_name]["value_examples"] = \
                        similar_entities[table_name][col_name]

    return filtered_schema

def full_columns_with_entities(
    tentative_schema: Dict[str, Dict[str, Dict[str, Any]]],
    similar_entities: Dict[str, Dict[str, List[str]]],
) -> Dict[str, Dict[str, Any]]:
    """
    Creates a complete schema that includes all tables and columns, adding VALUE EXAMPLES
    from similar_entities where available.

    Args:
        db_name (str): The database name
        similar_entities (Dict[str, Dict[str, List[str]]]): Table->column->list of similar entities

    Returns:
        Dict[str, Dict[str, Any]]: Complete schema with value examples added where available
    """
    # Get the complete schema
    #full_schema = get_db_schema(db_name)
    enriched_schema: Dict[str, Dict[str, Any]] = {}

    # Process all tables and columns
    for table_name, table_info in tentative_schema.items():
        enriched_schema[table_name] = {"columns": {}}
        
        # Process all columns
        for col_name, col_info in table_info["columns"].items():
            # Copy original column info
            enriched_schema[table_name]["columns"][col_name] = col_info.copy()
            
            # Add VALUE EXAMPLES if column is in similar_entities
            if (table_name in similar_entities and 
                col_name in similar_entities[table_name]):
                enriched_schema[table_name]["columns"][col_name]["value_examples"] = \
                    similar_entities[table_name][col_name]

    return enriched_schema
