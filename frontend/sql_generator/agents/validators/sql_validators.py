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
Validators for SQL generation agents.
"""

import re
from typing import List, Optional
from pydantic_ai import RunContext, ModelRetry

from ..core.agent_result_models import SqlResponse, InvalidRequest
from model.sql_generation_deps import SqlGenerationDeps
# Temporarily comment out to resolve import issues
# from model.sql_meta_info import SQLMetaInfo
from helpers.logging_config import get_logger
from helpers.dual_logger import log_info

logger = get_logger(__name__)


def get_executability_test_query(sql: str, database_type: str) -> str:
    """
    Returns the appropriate query to test SQL executability for the database type.
    Uses EXPLAIN or equivalent commands to validate syntax without full execution.
    
    Args:
        sql: The SQL query to test
        database_type: The type of database
    
    Returns:
        str: The query to execute for testing (EXPLAIN or equivalent)
    """
    db_type = database_type.lower()
    
    # PostgreSQL, MySQL, SQLite, MariaDB support standard EXPLAIN
    if db_type in ['postgresql', 'mysql', 'sqlite', 'mariadb']:
        return f"EXPLAIN {sql}"
    
    # SQL Server uses SET SHOWPLAN_ALL
    elif db_type in ['mssql', 'sqlserver']:
        return f"SET SHOWPLAN_ALL ON; {sql}; SET SHOWPLAN_ALL OFF;"
    
    # Oracle uses EXPLAIN PLAN FOR
    elif db_type in ['oracle']:
        return f"EXPLAIN PLAN FOR {sql}"
    
    # For unknown databases, fallback to the original query with a warning
    # This will execute the actual query but should still catch syntax errors
    else:
        logger.warning(f"Unknown database type '{database_type}', using original query for testing")
        return sql


class SqlValidators:
    """
    Validators for SQL generation agents.
    """
    
    def __init__(self, test_exec_agent=None, dbmanager=None):
        # test_exec_agent parameter kept for backward compatibility but no longer used
        self.dbmanager = dbmanager
    
    def create_sql_validator(self):
        """
        Create a validator for SQL generation agents.
        
        Returns:
            Async validator function
        """
        async def validate_sql_creation(ctx: RunContext[SqlGenerationDeps], response: SqlResponse):
            logger.debug(f"SQL validator started for agent response, dbmanager={self.dbmanager is not None}")
            
            if isinstance(response, InvalidRequest):
                logger.debug(f"Invalid request received: {response.error_message} - triggering retry")
                raise ModelRetry('Invalid request')
            
            sql = response.answer
            logger.debug(f"Raw SQL received from agent: {sql}")
            
            # Step 1: Check if it's a SELECT statement first
            if not sql.upper().strip().startswith('SELECT'):
                logger.debug(f"Invalid SQL query - not a SELECT statement: {sql} - triggering retry")
                ctx.deps.last_execution_error = "Generated SQL is not a SELECT query"
                raise ModelRetry('Create a SELECT query. Only SELECT statements are allowed for data retrieval.')
            
            # Always save the generated SQL to state for debugging, even if validation fails
            ctx.deps.last_SQL = sql
            logger.debug(f"SQL saved to state.last_SQL: {sql}")
            
            # Step 2: Apply database-specific sanitization
            db_type = ctx.deps.db_type  # Access from lightweight deps
            logger.debug(f"Database type for sanitization: {db_type}")
            
            try:
                sql = self._sanitize_sql_for_database(sql, db_type)
                logger.debug(f"SQL after {db_type} sanitization: {sql}")
            except ValueError as e:
                error_msg = f"SQL is not compatible with {db_type} database: {str(e)}"
                logger.debug(error_msg + " - triggering retry")
                ctx.deps.last_execution_error = error_msg
                raise ModelRetry(f"Please generate SQL compatible with {db_type} database. {str(e)}")
            try:
                # Step 3: Test SQL executability first using EXPLAIN or equivalent
                logger.debug(f"Step 1: Testing SQL executability")
                database_type = ctx.deps.db_type  # Access from lightweight deps
                logger.debug(f"Database type detected: {database_type}")
                
                try:
                    # Get the appropriate test query (EXPLAIN or equivalent)
                    test_query = get_executability_test_query(sql, database_type)
                    logger.debug(f"Testing SQL executability using: {test_query[:100]}...")
                    
                    # Execute EXPLAIN query using dbmanager if available
                    if self.dbmanager:
                        logger.debug(f"Executing EXPLAIN query to validate SQL syntax, dbmanager type: {type(self.dbmanager)}")
                        try:
                            # Execute the EXPLAIN query to validate syntax
                            logger.debug(f"Executing: {test_query[:100]}...")
                            self.dbmanager.execute_sql(sql=test_query, params={})
                            logger.debug(f"SQL executability test successful - syntax is valid")
                        except Exception as explain_error:
                            logger.debug(f"EXPLAIN failed: {explain_error}")
                            error_msg = f"SQL syntax validation failed: {str(explain_error)}"
                            logger.debug(error_msg + " - will trigger retry")
                            ctx.deps.last_execution_error = error_msg
                            # Re-raise to trigger ModelRetry
                            raise Exception(error_msg)
                    else:
                        # Fallback to lightweight validation without dbmanager
                        logger.warning("dbmanager not available - skipping EXPLAIN validation in parallel mode")
                        logger.debug("Using lightweight validation only")
                    
                except Exception as e:
                    error_msg = f"SQL executability test failed: {str(e)}"
                    logger.debug(error_msg + " - triggering retry with hints")
                    ctx.deps.last_execution_error = error_msg
                    raise ModelRetry(f"SQL execution failed during executability test. {error_msg}. Please fix the SQL syntax, ensure all referenced tables and columns exist, and verify the query structure is correct.")
                
                logger.debug("SQL validation passed successfully")
                
                # Step 4: Check for empty results if configured and dbmanager is available
                if ctx.deps.treat_empty_result_as_error and self.dbmanager:
                    logger.debug(f"Step 4: treat_empty_result_as_error=True, checking for empty results")
                    try:
                        # Execute the actual SQL to check for empty results
                        result = self.dbmanager.execute_sql(sql=sql, params={})
                        if not result or len(result) == 0:
                            logger.warning("SQL returned empty result set")
                            # Trigger empty result error
                            empty_result_error = True
                        else:
                            logger.debug(f"SQL returned {len(result)} rows - not empty")
                            empty_result_error = False
                    except Exception as e:
                        logger.error(f"Error checking for empty results: {e}")
                        # Don't fail on this check, just log it
                        empty_result_error = False
                    
                    if empty_result_error:
                        error_message = (
                            "EMPTY RESULT ERROR\n\n"
                            "Generated SQL Statement:\n"
                            f"```sql\n{sql}\n```\n\n"
                            "The query executed successfully but returned zero records.\n"
                            "Action Required: Please revise the SQL to return meaningful data.\n"
                            "Consider:\n"
                            "  • Checking filter conditions (WHERE clauses)\n"
                            "  • Verifying JOIN conditions\n"
                            "  • Ensuring the queried tables contain relevant data\n"
                            "  • Adjusting date ranges or other constraints"
                        )
                        
                        logger.debug(f"Empty result detected with treat_empty_result_as_error=True - triggering ModelRetry")
                        
                        # ModelRetry is a normal retry mechanism, not an error - log as info
                        log_info("Empty result detected - ModelRetry will be triggered for retry with additional context")
                        
                        ctx.deps.last_execution_error = f"Empty result error. {error_message}"
                        raise ModelRetry(error_message)
                elif ctx.deps.treat_empty_result_as_error and not self.dbmanager:
                    logger.warning("treat_empty_result_as_error=True but dbmanager not available - cannot check")
                else:
                    logger.debug(f"Step 4: treat_empty_result_as_error=False: Skipping empty result check")
                
                # Update the SQL in state again (in case it was modified during validation)
                ctx.deps.last_SQL = sql
                ctx.deps.last_generation_success = True
                logger.debug(f"SQL validation completed successfully")
                
            except ModelRetry:
                # Re-raise ModelRetry exceptions to ensure they propagate to the agent
                raise
            except Exception as e:
                logger.error(f"Exception during SQL validation: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                
                # Get the SQL statement that caused the exception
                failed_sql = ctx.deps.last_SQL or sql or "SQL statement not available"
                
                # Create comprehensive error message for the exception
                error_message = self._create_exception_error_message(failed_sql, e)
                
                # ModelRetry is a normal retry mechanism, log as info
                log_info("SQL execution exception - ModelRetry will be triggered with error details")
                
                # Create SQL metadata for tracking
                ctx.deps.last_execution_error = f"SQL execution failed. {error_message}"
                ctx.deps.last_generation_success = False
                
                logger.error(f"SQL validation failed - SQL was saved to state but marked as failed")
                raise ModelRetry(error_message)  # This should propagate up
        return validate_sql_creation
    
    def _format_test_results(self, test_results: Optional[List[str]]) -> dict:
        """
        Parse and format test results for better readability.
        
        Args:
            test_results: List of test result strings
            
        Returns:
            Dictionary with formatted test results including passed/failed counts
        """
        if not test_results:
            return {
                "total_tests": 0,
                "passed_tests": [],
                "failed_tests": [],
                "summary": "No test results available"
            }
        
        passed_tests = []
        failed_tests = []
        
        for i, result in enumerate(test_results):
            test_info = {
                "test_number": i + 1,
                "description": result.strip(),
                "status": "unknown"
            }
            
            # Try to determine if test passed or failed based on common patterns
            result_lower = result.lower()
            if any(keyword in result_lower for keyword in ["pass", "passed", "success", "correct", "valid"]):
                test_info["status"] = "passed"
                passed_tests.append(test_info)
            elif any(keyword in result_lower for keyword in ["fail", "failed", "error", "incorrect", "invalid", "wrong"]):
                test_info["status"] = "failed"
                failed_tests.append(test_info)
            else:
                # If we can't determine status, assume it's a failure since we're in error handling
                test_info["status"] = "failed"
                failed_tests.append(test_info)
        
        return {
            "total_tests": len(test_results),
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "summary": f"{len(passed_tests)} passed, {len(failed_tests)} failed out of {len(test_results)} total tests"
        }

    def _create_detailed_error_message(self, failed_sql: str, test_results_formatted: dict) -> str:
        """
        Create a comprehensive, structured error message for ModelRetry.
        
        Args:
            failed_sql: The SQL statement that failed validation
            test_results_formatted: Formatted test results from _format_test_results
            
        Returns:
            Detailed error message string
        """
        message_parts = [
            "SQL VALIDATION FAILED",
            "",
            "Generated SQL Statement:",
            f"```sql",
            failed_sql,
            f"```",
            "",
            f"Test Results Summary: {test_results_formatted['summary']}",
            ""
        ]
        
        # Add failed tests section
        if test_results_formatted['failed_tests']:
            message_parts.extend([
                "Failed Tests:",
                ""
            ])
            for test in test_results_formatted['failed_tests']:
                message_parts.append(f"  • Test {test['test_number']}: {test['description']}")
            message_parts.append("")
        
        # Add passed tests section if any
        if test_results_formatted['passed_tests']:
            message_parts.extend([
                "Passed Tests:",
                ""
            ])
            for test in test_results_formatted['passed_tests']:
                message_parts.append(f"  • Test {test['test_number']}: {test['description']}")
            message_parts.append("")
        
        # Add guidance
        message_parts.extend([
            "Action Required:",
            "Please revise the SQL statement to address the failing tests above.",
            "Focus on the specific issues identified in the failed tests.",
            ""
        ])
        
        return "\n".join(message_parts)

    def _add_schema_to_sql(self, sql: str, schema: str) -> str:
        """
        Adds a schema to table names in an SQL query using regex.
        Handles both quoted and unquoted table names, including those in subqueries.
        """
        
        # Pattern 1: Handle quoted table names (e.g., "table_name")
        # Matches FROM/JOIN followed by quoted table names that don't already have a schema
        sql = re.sub(r'(?i)\b(FROM|JOIN)\s+"([^"]+)"(?!\.)(?=\s|$|AS\b|\))',
                     fr'\1 {schema}."\2"',
                     sql)
        
        # Pattern 2: Handle unquoted table names (e.g., table_name)
        # Matches FROM/JOIN followed by unquoted table names that don't already have a schema
        # Enhanced to handle more cases including parentheses and various whitespace scenarios
        sql = re.sub(r'(?i)\b(FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?!\s*\.)(?=\s|$|AS\b|\)|,)',
                     fr'\1 {schema}.\2',
                     sql)
        
        return sql

    def _auto_quote_identifiers(self, sql: str, db_type: str) -> str:
        """
        Automatically quote identifiers that contain spaces or special characters.
        
        Args:
            sql: The SQL query
            db_type: Database type (lowercase)
        
        Returns:
            SQL with properly quoted identifiers
        """
        
        # For now, return the SQL as-is since auto-quoting is complex
        # The system prompt should handle proper quoting
        return sql
    
    def _sanitize_sql_for_database(self, sql: str, db_type: str) -> str:
        """
        Sanitize SQL for specific database type, handling quote characters and syntax differences.
        
        Args:
            sql: The SQL query to sanitize
            db_type: Database type (postgresql, mysql, mariadb, sqlite, oracle, sqlserver, mssql)
        
        Returns:
            Sanitized SQL compatible with the target database
        
        Raises:
            ValueError: If SQL cannot be made compatible with the target database
        """
        
        db_type_lower = db_type.lower()
        sanitized_sql = sql
        
        # Step 0: Auto-quote unquoted column names with spaces or special characters
        # This is a safety net for when the model doesn't properly quote them
        sanitized_sql = self._auto_quote_identifiers(sanitized_sql, db_type_lower)
        
        # Step 1: Handle identifier quoting based on database type
        if db_type_lower in ['postgresql', 'oracle']:
            # PostgreSQL and Oracle use double quotes for identifiers
            # Convert backticks to double quotes
            sanitized_sql = re.sub(r'`([^`]+)`', r'"\1"', sanitized_sql)
            # Convert square brackets to double quotes
            sanitized_sql = re.sub(r'\[([^\]]+)\]', r'"\1"', sanitized_sql)
            
        elif db_type_lower in ['mysql', 'mariadb']:
            # MySQL and MariaDB use backticks for identifiers
            # Convert double quotes to backticks
            sanitized_sql = re.sub(r'"([^"]+)"', r'`\1`', sanitized_sql)
            # Convert square brackets to backticks
            sanitized_sql = re.sub(r'\[([^\]]+)\]', r'`\1`', sanitized_sql)
            
        elif db_type_lower in ['mssql', 'sqlserver']:
            # SQL Server uses square brackets for identifiers
            # Convert double quotes to square brackets
            sanitized_sql = re.sub(r'"([^"]+)"', r'[\1]', sanitized_sql)
            # Convert backticks to square brackets
            sanitized_sql = re.sub(r'`([^`]+)`', r'[\1]', sanitized_sql)
            
        elif db_type_lower == 'sqlite':
            # SQLite is flexible, supports both double quotes and backticks
            # We'll standardize to double quotes
            sanitized_sql = re.sub(r'`([^`]+)`', r'"\1"', sanitized_sql)
            sanitized_sql = re.sub(r'\[([^\]]+)\]', r'"\1"', sanitized_sql)
        
        if db_type_lower in ['mssql', 'sqlserver']:
            limit_match = re.search(r'\bLIMIT\s+(\d+)\b', sanitized_sql, re.IGNORECASE)
            if limit_match:
                limit_value = limit_match.group(1)
                sanitized_sql = re.sub(r'\bLIMIT\s+\d+\b', '', sanitized_sql, flags=re.IGNORECASE)
                # Add TOP after SELECT
                sanitized_sql = re.sub(r'\bSELECT\b', f'SELECT TOP {limit_value}', sanitized_sql, flags=re.IGNORECASE)
            
            # Handle OFFSET with OFFSET...ROWS FETCH NEXT...ROWS ONLY
            offset_match = re.search(r'\bOFFSET\s+(\d+)\b', sanitized_sql, re.IGNORECASE)
            if offset_match:
                # SQL Server requires ORDER BY with OFFSET
                if 'ORDER BY' not in sanitized_sql.upper():
                    raise ValueError(f"SQL Server requires ORDER BY clause when using OFFSET. Please add an ORDER BY clause to your query.")
                # Convert to SQL Server syntax
                sanitized_sql = re.sub(
                    r'\bOFFSET\s+(\d+)(?:\s+LIMIT\s+(\d+))?\b',
                    lambda m: f'OFFSET {m.group(1)} ROWS' + (f' FETCH NEXT {m.group(2)} ROWS ONLY' if m.group(2) else ''),
                    sanitized_sql,
                    flags=re.IGNORECASE
                )
        
        elif db_type_lower == 'oracle':
            # Oracle uses ROWNUM or FETCH FIRST n ROWS ONLY (12c+)
            limit_match = re.search(r'\bLIMIT\s+(\d+)\b', sanitized_sql, re.IGNORECASE)
            if limit_match:
                limit_value = limit_match.group(1)
                sanitized_sql = re.sub(r'\bLIMIT\s+\d+\b', '', sanitized_sql, flags=re.IGNORECASE)
                # Add FETCH FIRST n ROWS ONLY (Oracle 12c+)
                sanitized_sql = sanitized_sql.rstrip().rstrip(';') + f' FETCH FIRST {limit_value} ROWS ONLY'
        
        # Step 3: Handle boolean literals
        if db_type_lower in ['mssql', 'sqlserver', 'oracle']:
            # SQL Server and Oracle don't have native boolean type
            # Convert TRUE/FALSE to 1/0
            sanitized_sql = re.sub(r'\bTRUE\b', '1', sanitized_sql, flags=re.IGNORECASE)
            sanitized_sql = re.sub(r'\bFALSE\b', '0', sanitized_sql, flags=re.IGNORECASE)
        
        # Step 4: Handle string concatenation operator differences
        if db_type_lower in ['mssql', 'sqlserver']:
            # SQL Server uses + for string concatenation
            sanitized_sql = re.sub(r'\|\|', '+', sanitized_sql)
        elif db_type_lower in ['mysql', 'mariadb']:
            # MySQL uses CONCAT function, but also supports || in ANSI mode
            # We'll leave || as is, assuming ANSI mode or proper configuration
            pass
        
        # Step 5: Handle database-specific function differences
        if db_type_lower in ['mssql', 'sqlserver']:
            # SQL Server uses LEN instead of LENGTH
            sanitized_sql = re.sub(r'\bLENGTH\s*\(', 'LEN(', sanitized_sql, flags=re.IGNORECASE)
            # SQL Server uses GETDATE() instead of NOW()
            sanitized_sql = re.sub(r'\bNOW\s*\(\s*\)', 'GETDATE()', sanitized_sql, flags=re.IGNORECASE)
        
        elif db_type_lower == 'oracle':
            # Oracle uses LENGTH (same as PostgreSQL)
            # Oracle uses SYSDATE instead of NOW()
            sanitized_sql = re.sub(r'\bNOW\s*\(\s*\)', 'SYSDATE', sanitized_sql, flags=re.IGNORECASE)
            # Oracle uses SUBSTR instead of SUBSTRING
            sanitized_sql = re.sub(r'\bSUBSTRING\s*\(', 'SUBSTR(', sanitized_sql, flags=re.IGNORECASE)
        
        # Step 6: Validate basic SQL structure
        if not sanitized_sql.strip():
            raise ValueError("SQL query is empty after sanitization")
        
        logger.debug(f"SQL sanitized for {db_type}: Original: {sql[:100]}... -> Sanitized: {sanitized_sql[:100]}...")
        
        return sanitized_sql
    
    def _create_exception_error_message(self, failed_sql: str, exception: Exception) -> str:
        """
        Create a comprehensive, structured error message for exceptions during SQL validation.
        
        Args:
            failed_sql: The SQL statement that caused the exception
            exception: The exception that occurred
            
        Returns:
            Detailed error message string
        """
        exception_type = type(exception).__name__
        exception_message = str(exception)
        
        message_parts = [
            "SQL EXECUTION FAILED",
            "",
            "Generated SQL Statement:",
            f"```sql",
            failed_sql,
            f"```",
            "",
            f"Error Type: {exception_type}",
            f"Error Details: {exception_message}",
            "",
            "Action Required:",
            "Please revise the SQL statement to fix the execution error above.",
            "Common issues include:",
            "  • Syntax errors in the SQL query",
            "  • Invalid column or table names",
            "  • Data type mismatches",
            "  • Missing JOIN conditions",
            "  • Invalid function usage",
            ""
        ]
        
        return "\n".join(message_parts)
