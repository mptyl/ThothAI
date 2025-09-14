# MODEL-RETRY-REV.md

## Implementation Plan: ModelRetry Optimization for PydanticAI SQL Generator

### Objective
Create an optimized formatting function for ModelRetry messages that maximizes the PydanticAI agent’s ability to learn from its own mistakes during SQL generation.

---

## 1. Nuovo Modulo: `model_retry_formatter.py`

**Path:** `frontend/sql_generator/helpers/model_retry_formatter.py`

```python
# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Optimized ModelRetry error formatter for PydanticAI SQL generation.
Provides structured, progressive, and database-specific error messages
to maximize agent learning from validation failures.
"""

from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass
from helpers.logging_config import get_logger

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """Categories for ModelRetry errors."""
    SYNTAX_ERROR = "SYNTAX ERROR"
    EMPTY_RESULT = "EMPTY RESULT SET"
    VALIDATION_FAILED = "VALIDATION FAILED"
    EXECUTION_ERROR = "EXECUTION ERROR"
    SCHEMA_ERROR = "SCHEMA REFERENCE ERROR"


@dataclass
class ErrorContext:
    """Context information for error formatting."""
    sql: str
    db_type: str
    error: Optional[Exception] = None
    retry_count: int = 0
    question: Optional[str] = None
    available_tables: Optional[List[str]] = None
    previous_errors: Optional[List[str]] = None
    validation_results: Optional[List[Dict]] = None


class ModelRetryFormatter:
    """
    Optimized formatter for ModelRetry messages in SQL generation.
    Implements PydanticAI best practices for agent learning.
    """
    
    # Database-specific quote styles
    QUOTE_STYLES = {
        'postgresql': '"double quotes"',
        'mysql': '`backticks`',
        'mariadb': '`backticks`',
        'sqlserver': '[square brackets]',
        'mssql': '[square brackets]',
        'sqlite': '"double quotes" or `backticks`',
        'oracle': '"double quotes"'
    }
    
    # Database-specific function mappings
    FUNCTION_HINTS = {
        'postgresql': {
            'current_time': 'NOW()',
            'string_length': 'LENGTH()',
            'null_handling': 'COALESCE()',
            'string_concat': '||'
        },
        'mysql': {
            'current_time': 'NOW()',
            'string_length': 'LENGTH()',
            'null_handling': 'IFNULL()',
            'string_concat': 'CONCAT()'
        },
        'sqlserver': {
            'current_time': 'GETDATE()',
            'string_length': 'LEN()',
            'null_handling': 'ISNULL()',
            'string_concat': '+'
        },
        'mssql': {
            'current_time': 'GETDATE()',
            'string_length': 'LEN()',
            'null_handling': 'ISNULL()',
            'string_concat': '+'
        },
        'sqlite': {
            'current_time': 'datetime("now")',
            'string_length': 'LENGTH()',
            'null_handling': 'COALESCE()',
            'string_concat': '||'
        },
        'oracle': {
            'current_time': 'SYSDATE',
            'string_length': 'LENGTH()',
            'null_handling': 'NVL()',
            'string_concat': '||'
        }
    }
    
    # Database-specific LIMIT syntax
    LIMIT_SYNTAX = {
        'postgresql': 'LIMIT n OFFSET m',
        'mysql': 'LIMIT n OFFSET m',
        'mariadb': 'LIMIT n OFFSET m',
        'sqlserver': 'TOP n or OFFSET m ROWS FETCH NEXT n ROWS ONLY',
        'mssql': 'TOP n or OFFSET m ROWS FETCH NEXT n ROWS ONLY',
        'sqlite': 'LIMIT n OFFSET m',
        'oracle': 'FETCH FIRST n ROWS ONLY or ROWNUM <= n'
    }
    
    @classmethod
    def format_error(cls, 
                    category: ErrorCategory,
                    context: ErrorContext) -> str:
        """
        Main entry point for formatting ModelRetry errors.
        
        Args:
            category: The error category
            context: Error context with all relevant information
            
        Returns:
            Formatted error message optimized for agent learning
        """
        # Select appropriate formatter based on category
        if category == ErrorCategory.SYNTAX_ERROR:
            return cls._format_syntax_error(context)
        elif category == ErrorCategory.EMPTY_RESULT:
            return cls._format_empty_result_error(context)
        elif category == ErrorCategory.VALIDATION_FAILED:
            return cls._format_validation_error(context)
        elif category == ErrorCategory.EXECUTION_ERROR:
            return cls._format_execution_error(context)
        elif category == ErrorCategory.SCHEMA_ERROR:
            return cls._format_schema_error(context)
        else:
            return cls._format_generic_error(context)
    
    @classmethod
    def _format_syntax_error(cls, context: ErrorContext) -> str:
        """Format syntax errors with database-specific guidance."""
        db_type = context.db_type.lower()
        
        # Progressive refinement based on retry count
        if context.retry_count == 0:
            # First attempt - general guidance
            guidance_level = "GENERAL SYNTAX CHECK"
            specific_hints = cls._get_general_syntax_hints(db_type)
        elif context.retry_count == 1:
            # Second attempt - more specific
            guidance_level = "SPECIFIC SYNTAX PATTERNS"
            specific_hints = cls._get_specific_syntax_hints(db_type, context.error)
        else:
            # Third+ attempt - very explicit
            guidance_level = "EXPLICIT CORRECTIONS REQUIRED"
            specific_hints = cls._get_explicit_syntax_corrections(db_type, context.error)
        
        message = f"""{context.category.value} - {db_type.upper()} - Attempt {context.retry_count + 1}

Failed SQL Query:
```sql
{context.sql}
```

Error Details:
{str(context.error) if context.error else 'Syntax validation failed'}

{guidance_level}:
{specific_hints}

Database-Specific Requirements for {db_type.upper()}:
• Identifier Quoting: {cls.QUOTE_STYLES.get(db_type, 'Check documentation')}
• LIMIT Syntax: {cls.LIMIT_SYNTAX.get(db_type, 'Check documentation')}
• Current Time: {cls.FUNCTION_HINTS.get(db_type, {}).get('current_time', 'Check documentation')}
• String Length: {cls.FUNCTION_HINTS.get(db_type, {}).get('string_length', 'Check documentation')}

Action Required:
1. Fix the syntax error identified above
2. Ensure all identifiers are properly quoted for {db_type}
3. Verify function names match {db_type} syntax
4. Check that the query structure is valid

Generate a corrected {db_type}-compatible SQL query."""
        
        return message
    
    @classmethod
    def _format_empty_result_error(cls, context: ErrorContext) -> str:
        """Format empty result errors with investigation guidance."""
        
        # Progressive hints based on retry count
        if context.retry_count == 0:
            investigation_approach = """
Initial Investigation:
• Check if WHERE conditions are too restrictive
• Verify that the tables contain data
• Consider if JOIN conditions might exclude all records"""
        elif context.retry_count == 1:
            investigation_approach = """
Deeper Investigation:
• Try removing WHERE conditions one by one
• Change INNER JOIN to LEFT JOIN where appropriate
• Check date ranges - are they within data bounds?
• Verify column values actually exist in the data"""
        else:
            investigation_approach = """
Systematic Debugging:
• Start with a simple SELECT * FROM table LIMIT 5
• Gradually add conditions back to identify the issue
• Use COUNT(*) to check data availability
• Consider if the question implies non-existent data"""
        
        tables_info = ""
        if context.available_tables:
            tables_info = f"\nAvailable Tables: {', '.join(context.available_tables)}"
        
        question_info = ""
        if context.question:
            question_info = f"\nOriginal Question: {context.question}"
        
        message = f"""{ErrorCategory.EMPTY_RESULT.value} - Attempt {context.retry_count + 1}

Query Executed Successfully But Returned No Data:
```sql
{context.sql}
```
{question_info}
{tables_info}

{investigation_approach}

Suggested Query Modifications:
1. Relax WHERE conditions:
   - Remove date filters temporarily
   - Use LIKE '%value%' instead of exact matches
   - Use OR instead of AND where logical

2. Adjust JOIN strategy:
   - Replace INNER JOIN with LEFT JOIN
   - Check if join columns have matching values
   - Verify foreign key relationships

3. Verify data existence:
   - Run: SELECT COUNT(*) FROM main_table
   - Check if filtered columns have expected values
   - Ensure date ranges overlap with data

Previous Errors: {len(context.previous_errors) if context.previous_errors else 0} attempts made

Action Required:
Generate a revised query that will return meaningful results.
Consider whether the question can be answered with available data."""
        
        return message
    
    @classmethod
    def _format_validation_error(cls, context: ErrorContext) -> str:
        """Format validation errors with test results."""
        
        if not context.validation_results:
            # No test results available
            return cls._format_generic_validation_error(context)
        
        failed_tests = [t for t in context.validation_results if not t.get('passed', False)]
        passed_tests = [t for t in context.validation_results if t.get('passed', False)]
        
        failed_details = ""
        if failed_tests:
            failed_details = "\n❌ Failed Validations:\n"
            for i, test in enumerate(failed_tests, 1):
                failed_details += f"   {i}. {test.get('name', 'Test')}: {test.get('error', 'Failed')}\n"
                if test.get('suggestion'):
                    failed_details += f"      Fix: {test['suggestion']}\n"
        
        passed_info = ""
        if passed_tests:
            passed_info = f"\n✓ Passed Validations: {len(passed_tests)} tests"
        
        message = f"""{ErrorCategory.VALIDATION_FAILED.value} - {len(failed_tests)} Issues Found - Attempt {context.retry_count + 1}

Current SQL:
```sql
{context.sql}
```

{failed_details}
{passed_info}

Resolution Strategy:
1. Address critical issues first (syntax, missing tables/columns)
2. Fix semantic issues next (logic, joins, conditions)
3. Optimize for performance last

Action Required:
Fix each failed validation in priority order.
Maintain all passing validations while fixing issues."""
        
        return message
    
    @classmethod
    def _format_execution_error(cls, context: ErrorContext) -> str:
        """Format execution errors with specific guidance."""
        
        error_str = str(context.error).lower() if context.error else ""
        
        # Detect specific error patterns and provide targeted guidance
        if "column" in error_str and ("does not exist" in error_str or "not found" in error_str):
            specific_guidance = """
Column Reference Error Detected:
• Verify column names match schema exactly (case-sensitive in some databases)
• Check for typos in column names
• Ensure columns exist in the referenced tables
• Use proper table aliases if using joins
• Verify column is in SELECT when used in GROUP BY"""
            
        elif "table" in error_str and ("does not exist" in error_str or "not found" in error_str):
            specific_guidance = """
Table Reference Error Detected:
• Verify table names match schema exactly
• Check if schema prefix is needed (e.g., schema.table)
• Ensure table exists in the database
• Check for typos in table names
• Verify you have permissions to access the table"""
            
        elif "syntax" in error_str or "parse" in error_str:
            specific_guidance = """
SQL Syntax Error Detected:
• Check for missing commas between columns
• Verify parentheses are balanced
• Ensure keywords are spelled correctly
• Check quote matching for strings
• Verify comment syntax if used"""
            
        elif "group by" in error_str:
            specific_guidance = """
GROUP BY Error Detected:
• All non-aggregate columns in SELECT must be in GROUP BY
• Aggregate functions (COUNT, SUM, etc.) cannot be in GROUP BY
• Check column aliases usage in GROUP BY
• Verify expression compatibility"""
            
        elif "join" in error_str or "on" in error_str:
            specific_guidance = """
JOIN Error Detected:
• Verify join columns exist in both tables
• Check data type compatibility between join columns
• Ensure proper join syntax (INNER/LEFT/RIGHT JOIN ... ON)
• Verify table aliases are defined before use"""
            
        else:
            specific_guidance = """
General Execution Error:
• Review the complete query structure
• Check data type compatibility in comparisons
• Verify function usage is correct
• Ensure proper permissions exist
• Check for reserved keywords used as identifiers"""
        
        message = f"""{ErrorCategory.EXECUTION_ERROR.value} - {type(context.error).__name__ if context.error else 'Unknown'} - Attempt {context.retry_count + 1}

SQL Statement:
```sql
{context.sql}
```

Error Type: {type(context.error).__name__ if context.error else 'Unknown'}
Error Details: {str(context.error) if context.error else 'Execution failed'}

{specific_guidance}

Progressive Debugging Steps:
1. Isolate the error - try running parts of the query
2. Verify all referenced objects exist
3. Check data types and compatibility
4. Test with simplified conditions
5. Build up complexity gradually

Action Required:
Revise the SQL to fix the execution error.
Focus on the specific issue identified above."""
        
        return message
    
    @classmethod
    def _format_schema_error(cls, context: ErrorContext) -> str:
        """Format schema-related errors."""
        
        message = f"""{ErrorCategory.SCHEMA_ERROR.value} - Attempt {context.retry_count + 1}

SQL with Schema Issues:
```sql
{context.sql}
```

Error: {str(context.error) if context.error else 'Schema reference error'}

Common Schema Issues:
• Table or column doesn't exist in the database
• Case sensitivity mismatch (PostgreSQL is case-sensitive for quoted identifiers)
• Missing schema prefix (e.g., should be schema.table)
• Incorrect database/catalog reference
• View vs Table confusion

Available Tables:
{', '.join(context.available_tables) if context.available_tables else 'Not provided - verify table names'}

Action Required:
1. Verify exact table and column names from schema
2. Use correct case for identifiers
3. Include schema prefix if required
4. Generate SQL with correct schema references"""
        
        return message
    
    @classmethod
    def _format_generic_error(cls, context: ErrorContext) -> str:
        """Format generic errors when category is unknown."""
        
        message = f"""SQL GENERATION ERROR - Attempt {context.retry_count + 1}

Failed SQL:
```sql
{context.sql}
```

Error: {str(context.error) if context.error else 'Unknown error occurred'}

General Troubleshooting:
1. Verify SQL syntax is correct
2. Check all table and column references
3. Ensure data types are compatible
4. Verify query logic matches intent
5. Test with simplified version first

Action Required:
Review and correct the SQL statement based on the error above."""
        
        return message
    
    @classmethod
    def _format_generic_validation_error(cls, context: ErrorContext) -> str:
        """Format validation error when no test results available."""
        
        return f"""{ErrorCategory.VALIDATION_FAILED.value} - Attempt {context.retry_count + 1}

SQL Failed Validation:
```sql
{context.sql}
```

The SQL query did not pass validation checks.

Action Required:
1. Ensure query is a valid SELECT statement
2. Verify all syntax is correct for {context.db_type}
3. Check that query addresses the original question
4. Generate a corrected query"""
    
    @classmethod
    def _get_general_syntax_hints(cls, db_type: str) -> str:
        """Get general syntax hints for first retry attempt."""
        return f"""
• Check identifier quoting: {cls.QUOTE_STYLES.get(db_type, 'standard')}
• Verify function names are correct for {db_type}
• Ensure proper use of keywords and operators
• Check for missing commas or semicolons"""
    
    @classmethod
    def _get_specific_syntax_hints(cls, db_type: str, error: Optional[Exception]) -> str:
        """Get specific syntax hints for second retry attempt."""
        error_str = str(error).lower() if error else ""
        
        hints = f"""
• Identifier quoting must use {cls.QUOTE_STYLES.get(db_type, 'standard')}
• Functions: {', '.join(f"{k}: {v}" for k, v in cls.FUNCTION_HINTS.get(db_type, {}).items())}"""
        
        if "limit" in error_str:
            hints += f"\n• LIMIT syntax for {db_type}: {cls.LIMIT_SYNTAX.get(db_type, 'standard')}"
        
        return hints
    
    @classmethod
    def _get_explicit_syntax_corrections(cls, db_type: str, error: Optional[Exception]) -> str:
        """Get explicit corrections for third+ retry attempts."""
        
        corrections = f"""
EXACT SYNTAX REQUIRED FOR {db_type.upper()}:

1. Identifiers with spaces MUST use {cls.QUOTE_STYLES.get(db_type, 'quotes')}
   Example: {cls._get_identifier_example(db_type)}

2. Current timestamp function: {cls.FUNCTION_HINTS.get(db_type, {}).get('current_time', 'NOW()')}
   Example: SELECT {cls.FUNCTION_HINTS.get(db_type, {}).get('current_time', 'NOW()')} as current_time

3. String concatenation: {cls.FUNCTION_HINTS.get(db_type, {}).get('string_concat', '||')}
   Example: {cls._get_concat_example(db_type)}

4. LIMIT clause: {cls.LIMIT_SYNTAX.get(db_type, 'LIMIT n')}
   Example: {cls._get_limit_example(db_type)}"""
        
        return corrections
    
    @classmethod
    def _get_identifier_example(cls, db_type: str) -> str:
        """Get example of properly quoted identifier."""
        if db_type in ['postgresql', 'oracle']:
            return 'SELECT "Column Name" FROM "Table Name"'
        elif db_type in ['mysql', 'mariadb']:
            return 'SELECT `Column Name` FROM `Table Name`'
        elif db_type in ['sqlserver', 'mssql']:
            return 'SELECT [Column Name] FROM [Table Name]'
        else:
            return 'SELECT "Column Name" FROM "Table Name"'
    
    @classmethod
    def _get_concat_example(cls, db_type: str) -> str:
        """Get example of string concatenation."""
        if db_type in ['postgresql', 'sqlite', 'oracle']:
            return "SELECT first_name || ' ' || last_name"
        elif db_type in ['mysql', 'mariadb']:
            return "SELECT CONCAT(first_name, ' ', last_name)"
        elif db_type in ['sqlserver', 'mssql']:
            return "SELECT first_name + ' ' + last_name"
        else:
            return "SELECT first_name || ' ' || last_name"
    
    @classmethod
    def _get_limit_example(cls, db_type: str) -> str:
        """Get example of LIMIT syntax."""
        if db_type in ['postgresql', 'mysql', 'mariadb', 'sqlite']:
            return "SELECT * FROM table LIMIT 10 OFFSET 20"
        elif db_type in ['sqlserver', 'mssql']:
            return "SELECT TOP 10 * FROM table"
        elif db_type == 'oracle':
            return "SELECT * FROM table FETCH FIRST 10 ROWS ONLY"
        else:
            return "SELECT * FROM table LIMIT 10"
```

---

## 2. Modifiche a `sql_generation_deps.py`

**Path:** `frontend/sql_generator/model/sql_generation_deps.py`

### Campi da aggiungere alla classe `SqlGenerationDeps`:

```python
from typing import List
from pydantic import BaseModel, Field

class SqlGenerationDeps(BaseModel):
    """
    Minimal and pickleable dependencies for SQL generation agents.
    
    This class contains only the essential information needed by SQL generation
    agents and their validators, without any complex non-pickleable objects.
    """
    
    # Read-only database information (simple strings/bool)
    db_type: str
    db_schema_str: str = ""  # Database schema as string for error messages
    treat_empty_result_as_error: bool = False
    
    # Mutable fields that validators write to
    last_SQL: str = ""
    last_execution_error: str = ""
    last_generation_success: bool = False
    
    # NUOVI CAMPI per il tracking migliorato del ModelRetry:
    retry_count: int = 0  # Traccia il numero di retry dell'agente
    error_history: List[str] = Field(default_factory=list)  # Storia degli errori precedenti
    question: str = ""  # La domanda originale dell'utente per contesto
    available_tables: List[str] = Field(default_factory=list)  # Lista delle tabelle disponibili nel database
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = False  # Ensure only simple types
```

---

## 3. Modifiche a `sql_validators.py`

**Path:** `frontend/sql_generator/agents/validators/sql_validators.py`

### Import da aggiungere all'inizio del file:

```python
from helpers.model_retry_formatter import ModelRetryFormatter, ErrorCategory, ErrorContext
```

### Sostituzione completa del metodo `create_sql_validator`:

```python
def create_sql_validator(self):
    """
    Create a validator for SQL generation agents with optimized ModelRetry formatting.
    
    Returns:
        Async validator function
    """
    async def validate_sql_creation(ctx: RunContext[SqlGenerationDeps], response: SqlResponse):
        logger.debug(f"SQL validator started for agent response, dbmanager={self.dbmanager is not None}")
        
        # Incrementa il retry count basandosi sul contesto PydanticAI
        ctx.deps.retry_count = getattr(ctx, 'retry', 0)
        
        # Gestione InvalidRequest
        if isinstance(response, InvalidRequest):
            logger.debug(f"Invalid request received: {response.error_message} - triggering retry")
            
            error_context = ErrorContext(
                sql="",
                db_type=ctx.deps.db_type,
                retry_count=ctx.deps.retry_count,
                question=ctx.deps.question,
                available_tables=ctx.deps.available_tables,
                previous_errors=ctx.deps.error_history
            )
            
            error_msg = ModelRetryFormatter.format_error(
                ErrorCategory.VALIDATION_FAILED,
                error_context
            )
            
            ctx.deps.error_history.append("Invalid request: " + response.error_message)
            raise ModelRetry(error_msg)
        
        sql = response.answer
        logger.debug(f"Raw SQL received from agent: {sql}")
        
        # Step 1: Verifica che sia una SELECT statement
        if not sql.upper().strip().startswith('SELECT'):
            logger.debug(f"Invalid SQL query - not a SELECT statement: {sql} - triggering retry")
            
            error_context = ErrorContext(
                sql=sql,
                db_type=ctx.deps.db_type,
                retry_count=ctx.deps.retry_count,
                question=ctx.deps.question,
                available_tables=ctx.deps.available_tables,
                previous_errors=ctx.deps.error_history
            )
            
            error_msg = ModelRetryFormatter.format_error(
                ErrorCategory.VALIDATION_FAILED,
                error_context
            )
            
            ctx.deps.last_execution_error = error_msg
            ctx.deps.error_history.append("Not a SELECT statement")
            raise ModelRetry(error_msg)
        
        # Always save the generated SQL for debugging
        ctx.deps.last_SQL = sql
        logger.debug(f"SQL saved to state.last_SQL: {sql}")
        
        # Step 2: Sanitizzazione database-specific
        db_type = ctx.deps.db_type
        logger.debug(f"Database type for sanitization: {db_type}")
        
        try:
            sql = self._sanitize_sql_for_database(sql, db_type)
            logger.debug(f"SQL after {db_type} sanitization: {sql}")
        except ValueError as e:
            error_context = ErrorContext(
                sql=sql,
                db_type=ctx.deps.db_type,
                error=e,
                retry_count=ctx.deps.retry_count,
                question=ctx.deps.question,
                available_tables=ctx.deps.available_tables,
                previous_errors=ctx.deps.error_history
            )
            
            error_msg = ModelRetryFormatter.format_error(
                ErrorCategory.SYNTAX_ERROR,
                error_context
            )
            
            ctx.deps.last_execution_error = error_msg
            ctx.deps.error_history.append(f"Sanitization error: {str(e)}")
            raise ModelRetry(error_msg)
        
        try:
            # Step 3: Test di eseguibilità SQL usando EXPLAIN
            logger.debug(f"Step 3: Testing SQL executability")
            database_type = ctx.deps.db_type
            logger.debug(f"Database type detected: {database_type}")
            
            try:
                # Ottieni la query di test appropriata (EXPLAIN o equivalente)
                test_query = get_executability_test_query(sql, database_type)
                logger.debug(f"Testing SQL executability using: {test_query[:100]}...")
                
                # Esegui la query EXPLAIN usando dbmanager se disponibile
                if self.dbmanager:
                    logger.debug(f"Executing EXPLAIN query to validate SQL syntax")
                    try:
                        self.dbmanager.execute_sql(sql=test_query, params={})
                        logger.debug(f"SQL executability test successful - syntax is valid")
                    except Exception as explain_error:
                        logger.debug(f"EXPLAIN failed: {explain_error}")
                        
                        # Determine error category from the message
                        error_str = str(explain_error).lower()
                        if "column" in error_str or "table" in error_str:
                            category = ErrorCategory.SCHEMA_ERROR
                        elif "syntax" in error_str or "parse" in error_str:
                            category = ErrorCategory.SYNTAX_ERROR
                        else:
                            category = ErrorCategory.EXECUTION_ERROR
                        
                        error_context = ErrorContext(
                            sql=sql,
                            db_type=ctx.deps.db_type,
                            error=explain_error,
                            retry_count=ctx.deps.retry_count,
                            question=ctx.deps.question,
                            available_tables=ctx.deps.available_tables,
                            previous_errors=ctx.deps.error_history
                        )
                        
                        error_msg = ModelRetryFormatter.format_error(category, error_context)
                        
                        ctx.deps.last_execution_error = error_msg
                        ctx.deps.error_history.append(f"EXPLAIN error: {str(explain_error)}")
                        raise ModelRetry(error_msg)
                else:
                    logger.warning("dbmanager not available - skipping EXPLAIN validation")
                    
            except ModelRetry:
                raise
            except Exception as e:
                error_context = ErrorContext(
                    sql=sql,
                    db_type=ctx.deps.db_type,
                    error=e,
                    retry_count=ctx.deps.retry_count,
                    question=ctx.deps.question,
                    available_tables=ctx.deps.available_tables,
                    previous_errors=ctx.deps.error_history
                )
                
                error_msg = ModelRetryFormatter.format_error(
                    ErrorCategory.EXECUTION_ERROR,
                    error_context
                )
                
                ctx.deps.last_execution_error = error_msg
                ctx.deps.error_history.append(f"Executability test error: {str(e)}")
                raise ModelRetry(error_msg)
            
            logger.debug("SQL validation passed successfully")
            
            # Step 4: Controllo risultati vuoti se configurato
            if ctx.deps.treat_empty_result_as_error and self.dbmanager:
                logger.debug(f"Step 4: treat_empty_result_as_error=True, checking for empty results")
                try:
                    # Esegui il SQL effettivo per verificare risultati vuoti
                    result = self.dbmanager.execute_sql(sql=sql, params={})
                    if not result or len(result) == 0:
                        logger.warning("SQL returned empty result set")
                        
                        error_context = ErrorContext(
                            sql=sql,
                            db_type=ctx.deps.db_type,
                            retry_count=ctx.deps.retry_count,
                            question=ctx.deps.question,
                            available_tables=ctx.deps.available_tables,
                            previous_errors=ctx.deps.error_history
                        )
                        
                        error_msg = ModelRetryFormatter.format_error(
                            ErrorCategory.EMPTY_RESULT,
                            error_context
                        )
                        
                        logger.debug(f"Empty result detected - triggering ModelRetry")
                        log_info("Empty result detected - ModelRetry will be triggered for retry with additional context")
                        
                        ctx.deps.last_execution_error = error_msg
                        ctx.deps.error_history.append("Empty result set")
                        raise ModelRetry(error_msg)
                    else:
                        logger.debug(f"SQL returned {len(result)} rows - not empty")
                        
                except ModelRetry:
                    raise
                except Exception as e:
                    logger.error(f"Error checking for empty results: {e}")
                    # Do not fail on this check, just log
            elif ctx.deps.treat_empty_result_as_error and not self.dbmanager:
                logger.warning("treat_empty_result_as_error=True but dbmanager not available")
            else:
                logger.debug(f"Step 4: treat_empty_result_as_error=False: Skipping empty result check")
            
            # Update SQL in state (in case it changed during validation)
            ctx.deps.last_SQL = sql
            ctx.deps.last_generation_success = True
            logger.debug(f"SQL validation completed successfully")
            
        except ModelRetry:
            # Re-raise ModelRetry to propagate to the agent
            raise
        except Exception as e:
            logger.error(f"Exception during SQL validation: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            
            # Create a comprehensive error message for the exception
            error_context = ErrorContext(
                sql=ctx.deps.last_SQL or sql or "SQL statement not available",
                db_type=ctx.deps.db_type,
                error=e,
                retry_count=ctx.deps.retry_count,
                question=ctx.deps.question,
                available_tables=ctx.deps.available_tables,
                previous_errors=ctx.deps.error_history
            )
            
            error_msg = ModelRetryFormatter.format_error(
                ErrorCategory.EXECUTION_ERROR,
                error_context
            )
            
            log_info("SQL execution exception - ModelRetry will be triggered with error details")
            
            ctx.deps.last_execution_error = error_msg
            ctx.deps.last_generation_success = False
            ctx.deps.error_history.append(f"Validation exception: {str(e)}")
            
            logger.error(f"SQL validation failed - SQL was saved to state but marked as failed")
            raise ModelRetry(error_msg)
    
    return validate_sql_creation
```

### Methods to remove (replaced by the new formatter):

- `_format_test_results`
- `_create_detailed_error_message`
- `_create_exception_error_message`

---

## 4. Formatter Call Points

The `ModelRetryFormatter` is invoked at these points within the validator:

1. **InvalidRequest handling** - When the agent returns an invalid request
2. **Non-SELECT query** - When the generated SQL is not a SELECT
3. **Database sanitization failure** - When database-specific sanitization fails
4. **EXPLAIN test failure** - When the executability test fails
5. **Empty result detection** - When the query returns zero results
6. **Generic exceptions** - For any other exception during validation

---

## 5. Implementation Benefits

### Progressive Learning
- **Retry 0**: General suggestions
- **Retry 1**: Error-specific guidance
- **Retry 2+**: Explicit corrections with examples

### Database-Specific
- Customized quote styles for each database
- Appropriate functions per system
- Correct LIMIT syntax

### Preserved Context
- Full error history
- Original question always available
- Table list for reference

### Intelligent Categorization
- 5 well-defined error categories
- Automatic detection of error type
- Targeted guidance per category

### Concrete Examples
- Correct SQL patterns per database
- Specific syntax examples
- Before/after comparison for clarity
