# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
SQL Delimiter Corrector for ThothAI

This module provides functionality to correct SQL delimiters based on the target database type.
It handles both string literals and complex identifiers (table/column names with spaces or special characters).

The corrector ensures that SQL queries use the optimal delimiter syntax for each database:
- SQLite: backticks (`) for identifiers, single quotes (') for strings
- PostgreSQL: double quotes (") for identifiers, single quotes (') for strings  
- MySQL/MariaDB: backticks (`) for identifiers, single quotes (') for strings
- SQL Server: square brackets ([]) for identifiers, single quotes (') for strings
- Oracle: double quotes (") for identifiers (uppercase), single quotes (') for strings
"""

import re
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# Database delimiter configuration
DELIMITER_MAP = {
    'sqlite': {
        'identifier_open': '`',
        'identifier_close': '`',
        'string': "'"
    },
    'postgresql': {
        'identifier_open': '"',
        'identifier_close': '"',
        'string': "'"
    },
    'postgres': {  # Alias for postgresql
        'identifier_open': '"',
        'identifier_close': '"',
        'string': "'"
    },
    'mysql': {
        'identifier_open': '`',
        'identifier_close': '`',
        'string': "'"
    },
    'mariadb': {
        'identifier_open': '`',
        'identifier_close': '`',
        'string': "'"
    },
    'mssql': {
        'identifier_open': '[',
        'identifier_close': ']',
        'string': "'"
    },
    'sqlserver': {  # Alias for mssql
        'identifier_open': '[',
        'identifier_close': ']',
        'string': "'"
    },
    'oracle': {
        'identifier_open': '"',
        'identifier_close': '"',
        'string': "'"
    }
}

# Default fallback delimiters
DEFAULT_DELIMITERS = {
    'identifier_open': '"',
    'identifier_close': '"',
    'string': "'"
}


def get_delimiters_for_db(db_type: str) -> Dict[str, str]:
    """
    Get the correct delimiters for a specific database type.
    
    Args:
        db_type (str): Database type (e.g., 'sqlite', 'postgresql', etc.)
        
    Returns:
        Dict[str, str]: Dictionary with delimiter configuration
    """
    if not db_type:
        return DEFAULT_DELIMITERS
        
    db_type_lower = db_type.lower().strip()
    
    # Handle common aliases and variations
    if db_type_lower in ['postgres', 'postgresql']:
        db_type_lower = 'postgresql'
    elif db_type_lower in ['mssql', 'sqlserver', 'sql server']:
        db_type_lower = 'mssql'
    elif db_type_lower in ['mysql']:
        db_type_lower = 'mysql'
    elif db_type_lower in ['mariadb']:
        db_type_lower = 'mariadb'
    elif db_type_lower in ['sqlite', 'sqlite3']:
        db_type_lower = 'sqlite'
    elif db_type_lower in ['oracle']:
        db_type_lower = 'oracle'
    
    return DELIMITER_MAP.get(db_type_lower, DEFAULT_DELIMITERS)


def is_valid_identifier_char(char: str) -> bool:
    """
    Check if a character is valid in an unquoted SQL identifier.
    
    Args:
        char (str): Character to check
        
    Returns:
        bool: True if character is valid in unquoted identifier
    """
    return char.isalnum() or char == '_'


def needs_delimiter(identifier: str) -> bool:
    """
    Determine if an identifier needs to be delimited.
    
    Identifiers need delimiters if they:
    - Contain spaces
    - Contain special characters (not alphanumeric or underscore)
    - Are SQL reserved keywords (basic check)
    - Start with a number
    
    Args:
        identifier (str): The identifier to check
        
    Returns:
        bool: True if identifier needs delimiters
    """
    if not identifier:
        return False
    
    # Check if it contains spaces or special characters
    if any(not is_valid_identifier_char(char) for char in identifier):
        return True
    
    # Check if it starts with a number
    if identifier[0].isdigit():
        return True
    
    # Basic reserved words check (extend as needed)
    # Note: Most databases allow common column names like 'status', 'count' without quotes
    # Only include truly reserved keywords that would cause syntax errors
    reserved_words = {
        'select', 'from', 'where', 'order', 'group', 'having', 'insert', 
        'update', 'delete', 'create', 'drop', 'alter', 'index', 'table',
        'view', 'procedure', 'function', 'trigger', 'database', 'schema',
        'union', 'join', 'inner', 'outer', 'left', 'right', 'cross',
        'exists', 'in', 'between', 'like', 'null', 'not', 'and', 'or',
        'case', 'when', 'then', 'else', 'end', 'distinct', 'all',
        'user', 'date', 'time', 'timestamp'  # These often need quoting
    }
    
    # Only quote reserved words that really need it, allow common names
    if identifier.lower() in reserved_words:
        return True
        
    return False


def is_string_context(sql: str, start_pos: int) -> bool:
    """
    Determine if a quoted segment is in a string context (value) or identifier context.
    
    This analyzes the SQL context around the quoted segment to determine if it's
    likely a string literal (after =, IN, etc.) or an identifier (table/column name).
    
    Args:
        sql (str): Full SQL query
        start_pos (int): Start position of the quoted segment
        
    Returns:
        bool: True if this is likely a string literal, False if identifier
    """
    # Get text before the quote to analyze context
    before_text = sql[:start_pos].strip()
    
    if not before_text:
        return False  # Start of query, likely identifier
    
    # Common patterns that indicate string context (values)
    string_indicators = [
        '=', '!=', '<>', '<', '>', '<=', '>=',  # Comparison operators
        'IN', 'in',  # IN clause
        'LIKE', 'like',  # LIKE operator
        'ILIKE', 'ilike',  # Case-insensitive LIKE
        'VALUES', 'values',  # INSERT VALUES
        'VALUE', 'value',  # INSERT VALUE
    ]
    
    # Check if any string indicator is at the end of the before text
    for indicator in string_indicators:
        if before_text.upper().endswith(indicator.upper()):
            return True
        # Also check with parenthesis or comma before indicator
        if before_text.upper().endswith(f'({indicator.upper()}') or \
           before_text.upper().endswith(f', {indicator.upper()}') or \
           before_text.upper().endswith(f',{indicator.upper()}'):
            return True
    
    # Check for comma-separated values (likely in IN clause or VALUES)
    if before_text.endswith(',') or before_text.endswith('('):
        # Look further back for context
        words_before = before_text.upper().split()
        if len(words_before) >= 1 and words_before[-1] in ['IN', 'VALUES']:
            return True
        if len(words_before) >= 2 and words_before[-2] in ['IN', 'VALUES']:
            return True
    
    # Common identifier contexts
    identifier_indicators = [
        'SELECT', 'select',
        'FROM', 'from',
        'UPDATE', 'update',
        'JOIN', 'join',
        'LEFT JOIN', 'left join',
        'RIGHT JOIN', 'right join',
        'INNER JOIN', 'inner join',
        'ORDER BY', 'order by',
        'GROUP BY', 'group by',
        'WHERE', 'where',
        'ON', 'on',
        'AS', 'as',
    ]
    
    for indicator in identifier_indicators:
        if before_text.upper().endswith(indicator.upper()):
            return False  # This is likely an identifier
    
    # If we can't determine from context, assume identifier
    # This is safer as identifiers are more common than string literals
    return False


def extract_quoted_segments(sql: str) -> Tuple[str, Dict[str, Tuple[str, str]]]:
    """
    Extract quoted segments from SQL and replace them with placeholders.
    
    This helps us process the SQL without accidentally modifying content
    inside string literals or already-quoted identifiers.
    
    Args:
        sql (str): Original SQL query
        
    Returns:
        Tuple[str, Dict[str, Tuple[str, str]]]: 
            - SQL with placeholders
            - Dictionary mapping placeholder -> (content, quote_type)
    """
    placeholders = {}
    placeholder_counter = 0
    result_sql = sql
    
    # First handle single quoted strings (these are almost always string literals)
    single_quote_pattern = r"'([^'\\]|\\.)*'"
    matches = list(re.finditer(single_quote_pattern, result_sql))
    
    # Process matches in reverse order to avoid index shifting
    for match in reversed(matches):
        content = match.group(0)
        placeholder = f"__QUOTE_PLACEHOLDER_{placeholder_counter}__"
        placeholders[placeholder] = (content, 'string')
        
        # Replace the match with placeholder
        result_sql = result_sql[:match.start()] + placeholder + result_sql[match.end():]
        placeholder_counter += 1
    
    # Then handle other quote types, analyzing context to determine if string or identifier
    other_quote_patterns = [
        (r'"([^"\\]|\\.)*"', '"'),              # Double quoted
        (r'`([^`\\]|\\.)*`', '`'),              # Backtick quoted
        (r'\[([^\]\\]|\\.)*\]', '['),           # Square bracket quoted
    ]
    
    for pattern, quote_char in other_quote_patterns:
        matches = list(re.finditer(pattern, result_sql))
        # Process matches in reverse order to avoid index shifting
        for match in reversed(matches):
            content = match.group(0)
            
            # Determine if this is a string or identifier based on context
            if is_string_context(result_sql, match.start()):
                quote_type = 'string'
            else:
                quote_type = 'identifier'
            
            placeholder = f"__QUOTE_PLACEHOLDER_{placeholder_counter}__"
            placeholders[placeholder] = (content, quote_type)
            
            # Replace the match with placeholder
            result_sql = result_sql[:match.start()] + placeholder + result_sql[match.end():]
            placeholder_counter += 1
    
    return result_sql, placeholders


def restore_quoted_segments(sql: str, placeholders: Dict[str, Tuple[str, str]], 
                          delimiters: Dict[str, str]) -> str:
    """
    Restore quoted segments with corrected delimiters.
    
    Args:
        sql (str): SQL with placeholders
        placeholders (Dict[str, Tuple[str, str]]): Mapping of placeholders to content
        delimiters (Dict[str, str]): Target delimiter configuration
        
    Returns:
        str: SQL with corrected delimiters
    """
    result_sql = sql
    
    for placeholder, (content, quote_type) in placeholders.items():
        if quote_type == 'string':
            # For strings, always use single quotes and handle escaping
            inner_content = content[1:-1]  # Remove outer quotes
            
            # Handle escaping of single quotes in the content
            if delimiters['string'] == "'":
                # Escape single quotes by doubling them
                inner_content = inner_content.replace("'", "''")
                corrected_content = f"'{inner_content}'"
            else:
                # This shouldn't happen with our current config, but handle gracefully
                corrected_content = f"{delimiters['string']}{inner_content}{delimiters['string']}"
        
        elif quote_type == 'identifier':
            # For identifiers, use the target database's preferred delimiters
            inner_content = content[1:-1]  # Remove outer quotes
            
            # Check if this identifier actually needs delimiters
            if needs_delimiter(inner_content):
                # Handle special case for Oracle (uppercase identifiers)
                if delimiters.get('identifier_open') == '"' and \
                   delimiters.get('identifier_close') == '"' and \
                   'oracle' in str(delimiters).lower():
                    inner_content = inner_content.upper()
                
                corrected_content = f"{delimiters['identifier_open']}{inner_content}{delimiters['identifier_close']}"
            else:
                # If it doesn't need delimiters, use it unquoted
                corrected_content = inner_content
        
        else:
            # Unknown type, keep original
            corrected_content = content
        
        # Replace placeholder with corrected content
        result_sql = result_sql.replace(placeholder, corrected_content)
    
    return result_sql


def correct_sql_delimiters(sql: str, db_type: str) -> str:
    """
    Correct SQL delimiters based on the target database type.
    
    This function analyzes the SQL query and corrects both string literals
    and identifier delimiters to match the target database's preferred syntax.
    
    Args:
        sql (str): Original SQL query
        db_type (str): Target database type
        
    Returns:
        str: SQL query with corrected delimiters
        
    Example:
        >>> sql = 'SELECT "field name" FROM "my table" WHERE "status" = "active"'
        >>> correct_sql_delimiters(sql, 'sqlite')
        "SELECT `field name` FROM `my table` WHERE `status` = 'active'"
        >>> correct_sql_delimiters(sql, 'mssql')
        "SELECT [field name] FROM [my table] WHERE [status] = 'active'"
    """
    if not sql or not sql.strip():
        return sql
        
    if not db_type:
        logger.warning("No database type provided, using default delimiters")
        return sql
    
    try:
        # Get the correct delimiters for this database
        delimiters = get_delimiters_for_db(db_type)
        
        logger.debug(f"Correcting SQL delimiters for database type: {db_type}")
        logger.debug(f"Using delimiters: {delimiters}")
        
        # Extract quoted segments to avoid processing content inside quotes
        processed_sql, placeholders = extract_quoted_segments(sql)
        
        # Restore segments with corrected delimiters
        result_sql = restore_quoted_segments(processed_sql, placeholders, delimiters)
        
        logger.debug(f"Original SQL: {sql}")
        logger.debug(f"Corrected SQL: {result_sql}")
        
        return result_sql
        
    except Exception as e:
        logger.error(f"Error correcting SQL delimiters: {e}")
        logger.error(f"Original SQL: {sql}")
        logger.error(f"Database type: {db_type}")
        # Return original SQL on error to avoid breaking the query
        return sql


def test_delimiter_correction():
    """
    Test function to verify delimiter correction works correctly.
    This can be run independently to validate the functionality.
    """
    test_cases = [
        {
            'sql': 'SELECT "field name" FROM "my table" WHERE "status" = "active"',
            'db_type': 'sqlite',
            'description': 'SQLite: Double quotes to backticks for identifiers, single quotes for strings'
        },
        {
            'sql': 'SELECT "field name" FROM "my table" WHERE "status" = "active"',
            'db_type': 'mssql',
            'description': 'SQL Server: Double quotes to square brackets for identifiers'
        },
        {
            'sql': 'SELECT "field-name" FROM "my_table" WHERE "count" > "5"',
            'db_type': 'mysql',
            'description': 'MySQL: Complex identifiers with backticks, my_table needs no quotes'
        },
        {
            'sql': 'SELECT name, count FROM users WHERE status = "active"',
            'db_type': 'postgresql',
            'description': 'PostgreSQL: Simple identifiers, quoted string'
        },
        {
            'sql': 'SELECT "user name", "date-created" FROM "user table"',
            'db_type': 'sqlite',
            'description': 'SQLite: Multiple complex identifiers'
        },
        {
            'sql': 'INSERT INTO "products" ("product name", "price") VALUES ("Widget", "19.99")',
            'db_type': 'mysql',
            'description': 'MySQL: INSERT with mixed identifiers and values'
        }
    ]
    
    print("Running delimiter correction tests...")
    
    for i, test_case in enumerate(test_cases):
        result = correct_sql_delimiters(test_case['sql'], test_case['db_type'])
        print(f"Test {i+1}: {test_case['description']}")
        print(f"  Input:    {test_case['sql']}")
        print(f"  Result:   {result}")
        print(f"  DB Type:  {test_case['db_type']}")
        print()
        
        # Let's also test some edge cases
        if i == 0:  # Add some debug info for the first test
            print("  Debug: Testing context detection...")
            test_sql = test_case['sql']
            # Find positions of quotes for debugging
            import re
            matches = list(re.finditer(r'"[^"]*"', test_sql))
            for j, match in enumerate(matches):
                is_string = is_string_context(test_sql, match.start())
                print(f"    Quote {j+1} '{match.group(0)}' at pos {match.start()}: {'STRING' if is_string else 'IDENTIFIER'}")
            print()


if __name__ == "__main__":
    # Run tests when script is executed directly
    test_delimiter_correction()