# Copyright (c) 2025 Marco Pancotti
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Helper module for M-Schema generation.
Contains functions to create filtered schemas and convert them to M-Schema format.
"""

import random
from typing import Dict, Any



def create_filtered_schema(state) -> Dict[str, Any]:
    """
    Creates a new schema that contains only columns from full_schema that are present
    in at least one of the other two schemas (schema_with_examples or schema_from_vector_db).
    Always includes primary keys (pk_field) and foreign keys (fk_field) from every table,
    even if not present in the other schemas.
    
    Args:
        state: SystemState object containing the schema information
        
    Returns:
        Dict[str, Any]: A new schema with the filtered columns
    """
    filtered_schema = {}
    
    for table_name, table_info in state.full_schema.items():
        # Initialize the filtered table structure
        filtered_table = {
            "table_description": table_info.get("table_description", ""),
            "columns": {}
        }
        
        full_columns = table_info.get("columns", {})
        examples_columns = state.schema_with_examples.get(table_name, {}).get("columns", {})
        vector_columns = state.schema_from_vector_db.get(table_name, {}).get("columns", {})
        
        for column_name, column_info in full_columns.items():
            should_include = False
            
            # Always include if it's a primary key or foreign key
            if (column_info.get("pk_field") and 
                column_info.get("pk_field") not in ["", "0", 0, False]):
                should_include = True
            
            if (column_info.get("fk_field") and 
                column_info.get("fk_field") not in ["", "0", 0, False]):
                should_include = True
            
            # Include if present in at least one of the other schemas
            if column_name in examples_columns or column_name in vector_columns:
                should_include = True
            
            if should_include:
                # Create a copy of the column info from full_schema
                filtered_column_info = dict(column_info)
                
                # Merge additional information from other schemas if available
                if column_name in examples_columns:
                    examples_info = examples_columns[column_name]
                    # Add examples if available
                    if "examples" in examples_info:
                        filtered_column_info["examples"] = examples_info["examples"]
                
                if column_name in vector_columns:
                    vector_info = vector_columns[column_name]
                    # Add vector DB specific information if available
                    if "column_description" in vector_info and not filtered_column_info.get("column_description"):
                        filtered_column_info["column_description"] = vector_info["column_description"]
                
                filtered_table["columns"][column_name] = filtered_column_info
        
        # Only add the table if it has columns
        if filtered_table["columns"]:
            filtered_schema[table_name] = filtered_table
            
    state.filtered_schema = filtered_schema
    return filtered_schema


def to_mschema(candidate_schema: Dict[str, Any]) -> str:
    """
    Converts the candidate_schema to M-Schema format - a semi-structured schema representation
    optimized for LLM consumption in Text-to-SQL tasks.
    
    Format follows M-Schema specification without DB_ID section:
    - 【Schema】 section with CREATE TABLE statements
    - 【Foreign keys】 section with table1.column1=table2.column2 format
    
    Args:
        candidate_schema: The schema dictionary to transform
        
    Returns:
        str: The M-Schema representation of the candidate schema
    """
    if not candidate_schema:
        return "【Schema】\n-- No schema available"
        
    schema_lines = ["【Schema】"]
    foreign_keys = []
    
    for table_name, table_info in candidate_schema.items():
        # Table description as comment
        table_description = table_info.get("table_description", "").strip()
        if table_description:
            schema_lines.append(f"-- {table_description}")
        
        # Start CREATE TABLE statement
        schema_lines.append(f"CREATE TABLE {table_name} (")
        
        columns = table_info.get("columns", {})
        column_definitions = []
        
        for col_name, col_info in columns.items():
            # Build column definition
            data_type = col_info.get("data_format", "TEXT").upper()
            col_def = f"    {col_name} {data_type}"
            
            # Mark primary key explicitly
            pk_field = col_info.get("pk_field", "")
            if pk_field and pk_field not in ["", "0", 0, False]:
                col_def += " -- PRIMARY KEY"
            
            column_definitions.append(col_def)
            
            # Add column description if available
            col_description = col_info.get("column_description", "").strip()
            value_description = col_info.get("value_description", "").strip()
            
            if col_description:
                column_definitions.append(f"    -- {col_description}")
            elif value_description:
                column_definitions.append(f"    -- {value_description}")
            
            # Add examples if available from LSH or vector DB
            examples = col_info.get("examples", [])
            if examples and isinstance(examples, list):
                # Limit to first 5 examples and clean them
                clean_examples = []
                for ex in examples[:5]:
                    if ex is not None and str(ex).strip():
                        clean_examples.append(str(ex).strip())
                
                if clean_examples:
                    examples_str = ", ".join(clean_examples)
                    column_definitions.append(f"    -- Examples: {examples_str}")
            
            # Process foreign key relationships
            fk_field = col_info.get("fk_field", "").strip()
            if fk_field and fk_field not in ["", "0", 0, False]:
                # Handle multiple FK references separated by comma
                fk_refs = [ref.strip() for ref in fk_field.split(',') if ref.strip()]
                
                for fk_ref in fk_refs:
                    # Skip malformed descriptive strings
                    if fk_ref.lower().startswith("this column references"):
                        continue
                        
                    # Expect format: table.column
                    if '.' in fk_ref:
                        ref_table, ref_column = fk_ref.split('.', 1)
                        if ref_table.strip() and ref_column.strip():
                            foreign_keys.append(f"{table_name}.{col_name}={ref_table.strip()}.{ref_column.strip()}")
        
        # Add column definitions to table
        schema_lines.extend(column_definitions)
        
        # Close CREATE TABLE statement
        schema_lines.append(");")
        schema_lines.append("")  # Empty line between tables
    
    # Add foreign keys section if any exist
    if foreign_keys:
        schema_lines.append("【Foreign keys】")
        schema_lines.extend(foreign_keys)
    
    # Generate final M-Schema string
    return "\n".join(schema_lines)


def shuffle_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shuffle tables and columns order while preserving structure and relationships.
    
    This function randomizes the order of tables and columns to create diversity
    in schema presentation while maintaining all FK/PK relationships and data integrity.
    
    Args:
        schema: The schema dictionary to shuffle
        
    Returns:
        Dict[str, Any]: A new schema with shuffled table and column order
    """
    if not schema:
        return schema
    
    # Create a copy to avoid modifying original
    shuffled_schema = {}
    
    # Shuffle table order
    table_names = list(schema.keys())
    random.shuffle(table_names)
    
    for table_name in table_names:
        table_info = schema[table_name]
        shuffled_table = {
            "table_description": table_info.get("table_description", ""),
            "columns": {}
        }
        
        # Shuffle column order
        columns = table_info.get("columns", {})
        column_names = list(columns.keys())
        random.shuffle(column_names)
        
        # Rebuild columns dict with shuffled order
        for col_name in column_names:
            shuffled_table["columns"][col_name] = columns[col_name]
        
        shuffled_schema[table_name] = shuffled_table
    
    return shuffled_schema


def generate_dynamic_mschema(state, apply_shuffle: bool = True) -> str:
    """
    Generate a dynamic mschema based on schema_link_strategy with optional shuffle.
    
    This function creates an mschema on-the-fly for each agent run, optionally
    shuffling the order of tables and columns to increase diversity in generated outputs.
    
    Args:
        state: SystemState object containing schema information and strategy
        apply_shuffle: Whether to shuffle tables and columns order (default: True)
        
    Returns:
        str: M-Schema representation with optionally shuffled order
    """
    # Determine which schema to use based on strategy
    # Default to WITHOUT_SCHEMA_LINK if strategy not set
    schema_link_strategy = getattr(state, 'schema_link_strategy', 'WITHOUT_SCHEMA_LINK')
    
    if schema_link_strategy == "WITHOUT_SCHEMA_LINK":
        # Use enriched_schema (full schema with examples)
        if not hasattr(state, 'enriched_schema') or not state.enriched_schema:
            state.create_enriched_schema()
        base_schema = state.enriched_schema
    else:
        # WITH_SCHEMA_LINK - use filtered_schema
        if not hasattr(state, 'filtered_schema') or not state.filtered_schema:
            # Create filtered schema if it doesn't exist
            create_filtered_schema(state)
        base_schema = state.filtered_schema
    
    # Apply shuffle if requested
    if apply_shuffle and base_schema:
        base_schema = shuffle_schema(base_schema)
    
    # Convert to mschema format
    return to_mschema(base_schema)