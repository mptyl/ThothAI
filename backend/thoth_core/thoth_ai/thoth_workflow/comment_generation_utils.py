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

import json
import os
import re
from typing import Any

from thoth_core.models import LLMChoices
from thoth_core.thoth_ai.llm_client import ThothLLMClient, create_llm_client

# Import the database manager factory
from thoth_dbmanager import ThothDbFactory

def preprocess_template(template: str, variables: dict = None) -> str:
    """
    Process Haystack/Jinja2 style templates for use with Python's format() or manual rendering.
    
    This function handles:
    - {{variable}} syntax conversion to {variable}
    - Jinja2 control structures ({% if %}, {% for %}, etc.)
    - Complex nested structures with dot notation
    
    Args:
        template: Template string with Jinja2/Haystack syntax
        variables: Optional dict of variables for Jinja2 rendering
        
    Returns:
        Processed template string suitable for .format() or already rendered if Jinja2 is needed
    """
    import re
    
    # Check if template has Jinja2 control structures
    has_control_structures = bool(re.search(r'\{%.*?%\}', template))
    
    if has_control_structures and variables:
        # Use Jinja2 for full template rendering
        try:
            from jinja2 import Template
            jinja_template = Template(template)
            return jinja_template.render(**variables)
        except ImportError:
            # Jinja2 not available, fall back to simple replacement
            # Remove control structures
            template = re.sub(r'\{%.*?%\}', '', template)
    
    # Simple variable replacement for {{variable}} to {variable}
    # This regex handles simple variables and dot notation
    template = re.sub(r'\{\{[\s]*([a-zA-Z_][\w\.]*?)[\s]*\}\}', r'{\1}', template)
    
    return template

def output_to_json(output):
    """
    Extracts and parses JSON content from the output of a generator.

    This function searches for a JSON-like string enclosed in square brackets
    within the generator's response and attempts to parse it into a Python object.

    Args:
        output: The LLM response content (string) or LLMResponse object

    Returns:
        dict or None: The parsed JSON content if found and successfully parsed,
                      or None if no valid JSON content is found.

    Note:
        The function assumes that the JSON content is enclosed in square brackets.
    """
    # Handle both string and LLMResponse object
    if hasattr(output, 'content'):
        response = output.content
    else:
        response = str(output)
    
    # Try to find JSON array in the response
    # First try to find a clean JSON block
    json_match = re.search(r'```json\s*(\[.*?\])\s*```', response, re.DOTALL)
    if not json_match:
        # Try with any code block
        json_match = re.search(r'```\s*(\[.*?\])\s*```', response, re.DOTALL)
    if not json_match:
        # If no code block, try to find raw JSON array
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
    
    if json_match:
        # Determine which group to use based on what was matched
        if '```json' in response or '```' in response:
            # Code block found, use group 1 (content inside the block)
            json_str = json_match.group(1) if json_match.lastindex else json_match.group(0)
        else:
            # Raw JSON, use group 0 (entire match)
            json_str = json_match.group(0)
        
        try:
            # Clean up common formatting issues
            json_str = json_str.strip()
            # Remove any trailing commas before closing brackets
            json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
            
            parsed_json = json.loads(json_str)
            
            # Validate the structure for column comments
            if isinstance(parsed_json, list) and len(parsed_json) > 0:
                # Check if it has the expected structure
                first_item = parsed_json[0]
                if isinstance(first_item, dict):
                    # Handle both possible key names
                    if 'column_name' in first_item or 'name' in first_item:
                        # Normalize to use 'column_name' key
                        normalized = []
                        for item in parsed_json:
                            normalized_item = {}
                            # Use 'column_name' if present, otherwise use 'name'
                            normalized_item['column_name'] = item.get('column_name', item.get('name', ''))
                            # Use 'description' if present, otherwise use 'comment'
                            normalized_item['description'] = item.get('description', item.get('comment', ''))
                            normalized.append(normalized_item)
                        return normalized
            
            return parsed_json
            
        except json.JSONDecodeError as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"JSON parsing error: {e}")
            return None
    else:
        return None

def setup_default_comment_llm_model(setting) -> ThothLLMClient:
    """
    Set up and return the default language model for comment generation based on the provided settings.

    This function initializes a language model client for generating comments using LiteLLM,
    supporting multiple providers including OpenAI, Anthropic, Google, Mistral, Ollama, and others.

    Args:
        setting: An object containing configuration settings for the AI model.
                 Expected to have a 'comment_model' attribute with details about the model.

    Returns:
        ThothLLMClient: A configured LLM client instance for the specified provider.

    Raises:
        ValueError: If the provider is not supported.
    """
    ai_model = setting.comment_model
    return create_llm_client(ai_model)


def setup_sql_db(sql_db):
    """
    Set up and return a database component based on the provided SQL database configuration.

    This function initializes a database component using the modern ThothDbFactory,
    supporting PostgreSQL, SQLite, MySQL, MariaDB, SQLServer, and Oracle.
    It uses the configuration details provided in the sql_db parameter to establish
    a connection to the database.

    Args:
        sql_db: An object containing the SQL database configuration.
                Expected to have attributes:
                - db_type: The type of the database (e.g., 'PostgreSQL', 'SQLite')
                - db_host: The host address of the database (for PostgreSQL)
                - db_port: The port number for the database connection (for PostgreSQL)
                - db_name: The name of the database
                - schema: The schema to be used in the database (for PostgreSQL)
                - user_name: The username for database authentication (for PostgreSQL)
                - password: The password for database authentication (for PostgreSQL)
                - db_mode: The mode for SQLite database

    Returns:
        ThothDbManager: An initialized database manager component.

    Raises:
        ValueError: If the specified database type is not supported.
        Exception: If there's an error creating the database manager.

    Note:
        Uses the modern ThothDbFactory.create_manager() approach for database instantiation.
    """
    try:
        # Map Django model db_type to plugin identifiers
        db_type_mapping = {
            'PostgreSQL': 'postgresql',
            'SQLite': 'sqlite',
            'MySQL': 'mysql',
            'MariaDB': 'mariadb',
            'SQLServer': 'sqlserver',
            'Oracle': 'oracle'
        }
        
        plugin_db_type = db_type_mapping.get(sql_db.db_type)
        if not plugin_db_type:
            raise ValueError(f"Database type '{sql_db.db_type}' is not yet supported.")
        
        # Get DB_ROOT_PATH from environment or use default
        db_root_path = os.environ.get('DB_ROOT_PATH', 'data')
        
        # Prepare connection parameters
        connection_params = {}
        
        if plugin_db_type == 'sqlite':
            # SQLite uses database_path instead of separate host/port/database
            # Construct path following the same pattern as other database plugins: db_root_path/db_mode_databases/db_name/db_name.sqlite
            sqlite_dir = os.path.join(db_root_path, f"{sql_db.db_mode}_databases", sql_db.db_name)
            connection_params['database_path'] = os.path.join(sqlite_dir, f"{sql_db.db_name}.sqlite")
        else:
            # For other databases, use standard connection parameters
            connection_params.update({
                'host': sql_db.db_host,
                'port': sql_db.db_port,
                'database': sql_db.db_name,
                'user': sql_db.user_name,
                'password': sql_db.password
            })
            
            # Add schema if provided
            if sql_db.schema:
                connection_params['schema'] = sql_db.schema
        
        # Create manager using new factory
        manager = ThothDbFactory.create_manager(
            db_type=plugin_db_type,
            db_root_path=db_root_path,
            db_mode=sql_db.db_mode,
            **connection_params
        )
        
        return manager
        
    except Exception as e:
        raise Exception(f"Error setting up SQL database: {str(e)}")

def get_table_schema_safe(db_manager, table_name):
    """
    Safe wrapper to get table schema that works with all database plugins.
    
    This function first tries to use the get_table_schema method if available,
    and falls back to generating table structure information using get_columns method
    for databases that don't have traditional schemas (like SQLite).
    
    Args:
        db_manager: Database manager instance
        table_name: Name of the table to get schema/structure for
        
    Returns:
        str: Table structure information formatted for AI prompts
    """
    try:
        # First try the native get_table_schema method (for PostgreSQL, MySQL, etc.)
        if hasattr(db_manager, 'get_table_schema') and callable(getattr(db_manager, 'get_table_schema')):
            return db_manager.get_table_schema(table_name)
    except Exception as e:
        # If get_table_schema fails, fall through to the workaround
        pass
    
    # Fallback: generate table structure using get_columns method
    # This is particularly useful for SQLite and other databases without traditional schemas
    try:
        columns = db_manager.get_columns(table_name)
        if not columns:
            return f"Table: {table_name}\nNo column information available."
        
        # Build a formatted table structure string
        structure_lines = [f"Table: {table_name}"]
        structure_lines.append("Structure:")
        
        for column in columns:
            column_name = column.get('name', 'unknown')
            data_type = column.get('data_type', 'unknown')
            is_pk = column.get('is_pk', False)
            is_nullable = column.get('is_nullable', True)
            comment = column.get('comment', '')
            
            # Format column information
            column_info = f"  - {column_name}: {data_type}"
            
            # Add constraints
            constraints = []
            if is_pk:
                constraints.append("PRIMARY KEY")
            if not is_nullable:
                constraints.append("NOT NULL")
            
            if constraints:
                column_info += f" ({', '.join(constraints)})"
            
            if comment:
                column_info += f" -- {comment}"
            
            structure_lines.append(column_info)
        
        return "\n".join(structure_lines)
        
    except Exception as e:
        # If all else fails, return minimal information
        return f"Table: {table_name}\nError retrieving table structure: {str(e)}"
