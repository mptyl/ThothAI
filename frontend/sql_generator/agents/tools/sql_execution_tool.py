# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License, Version 2.0.
# See the LICENSE file in the project root for full license information.

"""
SQL Execution Tool for PydanticAI agents.
This tool allows agents to execute SQL queries without including the dbmanager in deps.
"""

from typing import Dict, Any, Optional
from pydantic_ai import Tool


def create_sql_execution_tool(dbmanager) -> Tool:
    """
    Create a SQL execution tool for PydanticAI agents.
    
    This tool keeps the dbmanager reference external to the agent deps,
    making the deps fully pickleable for parallel execution.
    
    Args:
        dbmanager: The database manager instance to use for SQL execution
        
    Returns:
        A Tool instance configured for SQL execution
    """
    
    async def execute_sql(sql: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a SQL query and return the result.
        
        Args:
            sql: The SQL query to execute
            params: Optional parameters for the SQL query
            
        Returns:
            Dictionary with:
                - success: Boolean indicating if execution was successful
                - result: Query result if successful, None otherwise
                - error: Error message if failed, None otherwise
        """
        try:
            result = dbmanager.execute_sql(sql=sql, params=params or {})
            return {
                "success": True,
                "result": result,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }
    
    return Tool(
        execute_sql,
        name="execute_sql",
        description="Execute SQL query against the database and return results or errors"
    )


# For backward compatibility if imported as a class
class SqlExecutionTool:
    """
    Factory class for creating SQL execution tools.
    """
    
    def __init__(self, dbmanager):
        """Store dbmanager for later tool creation."""
        self.dbmanager = dbmanager
    
    def create_tool(self) -> Tool:
        """Create and return the actual Tool instance."""
        return create_sql_execution_tool(self.dbmanager)