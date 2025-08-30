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