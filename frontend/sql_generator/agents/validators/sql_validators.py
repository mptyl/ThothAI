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
import os
import asyncio
from typing import Any, Dict, List, Optional
from pydantic_ai import RunContext, ModelRetry
from pydantic_ai.settings import ModelSettings

from ..core.agent_result_models import SqlResponse, InvalidRequest
from model.sql_generation_deps import SqlGenerationDeps
# Temporarily comment out to resolve import issues
# from model.sql_meta_info import SQLMetaInfo
from helpers.logging_config import get_logger
from helpers.dual_logger import log_info
from helpers.template_preparation import TemplateLoader
from helpers.model_retry_formatter import (
    ErrorCategory,
    ErrorContext,
    ModelRetryFormatter,
)
from model.evaluator_deps import EvaluatorDeps
from .relevance_guard import classify_tests, load_config_from_env

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
    
    def __init__(self, evaluator_agent=None, dbmanager=None):
        # evaluator_agent is used for evidence-critical gating
        self.dbmanager = dbmanager
        self.evaluator_agent = evaluator_agent

    def _raise_model_retry(
        self,
        ctx: RunContext[SqlGenerationDeps],
        category: ErrorCategory,
        *,
        sql: str = "",
        error_message: str = "",
        exception: Exception | None = None,
        validation_results: Optional[List[Dict[str, Any]]] = None,
        failed_tests: Optional[List[str]] = None,
        evidence_summary: Optional[Dict[str, Any]] = None,
        explain_error: str = "",
        additional_hints: Optional[List[str]] = None,
        available_tables: Optional[List[str]] = None,
    ) -> None:
        """Format and raise a ModelRetry with structured context."""

        ctx.deps.retry_attempt = ctx.retry
        context = ErrorContext(
            sql=sql or ctx.deps.last_SQL,
            db_type=ctx.deps.db_type,
            question=getattr(ctx.deps, "question", ""),
            retry_count=ctx.retry,
            error_message=error_message,
            exception=exception,
            validation_results=validation_results,
            failed_tests=failed_tests,
            evidence_summary=evidence_summary,
            explain_error=explain_error or ctx.deps.last_explain_error,
            previous_errors=list(ctx.deps.retry_history or []),
            additional_hints=additional_hints,
            available_tables=available_tables,
        )

        message = ModelRetryFormatter.format_error(category, context)
        history_entry = ModelRetryFormatter.build_history_entry(category, context)

        ctx.deps.retry_history.append(history_entry)
        # Keep only the latest 8 entries to avoid unbounded growth
        if len(ctx.deps.retry_history) > 8:
            ctx.deps.retry_history = ctx.deps.retry_history[-8:]

        if failed_tests is not None:
            ctx.deps.last_failed_tests = failed_tests
        if explain_error:
            ctx.deps.last_explain_error = explain_error

        derived_message = context.render_error_detail()
        ctx.deps.last_execution_error = derived_message
        ctx.deps.last_generation_success = False

        raise ModelRetry(message)

    @staticmethod
    def _is_empty_result(result: Any) -> bool:
        """Return True when an execution result does not contain data."""

        if result is None:
            return True
        if isinstance(result, (list, tuple, set)):
            return len(result) == 0
        if isinstance(result, dict):
            return len(result) == 0
        # SQLAlchemy returns RowMapping or Row, which behave like tuples
        if hasattr(result, "__len__") and hasattr(result, "__iter__"):
            try:
                return len(result) == 0
            except Exception:  # pragma: no cover - defensive
                pass
        return False
    
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
                reason = response.error_message or "Invalid SQL generation request"
                ctx.deps.last_execution_error = reason
                self._raise_model_retry(
                    ctx,
                    ErrorCategory.VALIDATION_FAILED,
                    error_message=reason,
                    additional_hints=["Ensure the response schema matches SqlResponse"],
                )
            
            sql = response.answer
            logger.debug(f"Raw SQL received from agent: {sql}")
            
            # Step 1: Check if it's a SELECT statement first
            if not sql.upper().strip().startswith('SELECT'):
                logger.debug(f"Invalid SQL query - not a SELECT statement: {sql} - triggering retry")
                ctx.deps.last_SQL = sql
                ctx.deps.last_execution_error = "Generated SQL is not a SELECT query"
                self._raise_model_retry(
                    ctx,
                    ErrorCategory.SYNTAX_ERROR,
                    sql=sql,
                    error_message="Create a SELECT query. Only SELECT statements are allowed for data retrieval.",
                    additional_hints=[
                        "Start the statement with SELECT",
                        "Avoid INSERT/UPDATE/DELETE operations in this context",
                    ],
                )
            
            # Always save the generated SQL to state for debugging, even if validation fails
            ctx.deps.last_SQL = sql
            logger.debug(f"SQL saved to state.last_SQL: {sql}")
            
            # Step 2: Apply database-specific sanitization
            db_type = ctx.deps.db_type  # Access from lightweight deps
            logger.debug(f"Database type for sanitization: {db_type}")
            
            try:
                sql = self._sanitize_sql_for_database(sql, db_type)
                logger.debug(f"SQL after {db_type} sanitization: {sql}")
                ctx.deps.last_SQL = sql
            except ValueError as e:
                error_msg = f"SQL is not compatible with {db_type} database: {str(e)}"
                logger.debug(error_msg + " - triggering retry")
                ctx.deps.last_execution_error = error_msg
                self._raise_model_retry(
                    ctx,
                    ErrorCategory.SCHEMA_ERROR,
                    sql=ctx.deps.last_SQL,
                    error_message=error_msg,
                    exception=e,
                    additional_hints=[
                        "Adjust identifier quoting for the target database",
                        "Verify LIMIT/OFFSET syntax matches the dialect",
                    ],
                )
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
                            ctx.deps.last_explain_error = error_msg
                            self._raise_model_retry(
                                ctx,
                                ErrorCategory.SYNTAX_ERROR,
                                sql=sql,
                                error_message=error_msg,
                                exception=explain_error,
                                additional_hints=[
                                    "Review the SQL around the position reported by EXPLAIN",
                                    "Ensure dialect-specific syntax (e.g., LIMIT/TOP) is correct",
                                ],
                            )
                    else:
                        # Fallback to lightweight validation without dbmanager
                        logger.warning("dbmanager not available - skipping EXPLAIN validation in parallel mode")
                        logger.debug("Using lightweight validation only")
                    
                except Exception as e:
                    error_msg = f"SQL executability test failed: {str(e)}"
                    logger.debug(error_msg + " - triggering retry with hints")
                    ctx.deps.last_execution_error = error_msg
                    ctx.deps.last_explain_error = error_msg
                    self._raise_model_retry(
                        ctx,
                        ErrorCategory.SYNTAX_ERROR,
                        sql=sql,
                        error_message=error_msg,
                        exception=e,
                        additional_hints=[
                            "Re-run EXPLAIN after correcting the syntax",
                            "Check table and column names against the schema",
                            "Ensure the query structure follows database conventions",
                        ],
                    )
                
                logger.debug("SQL validation passed successfully")
                
                # Step 4: Evidence-critical gating with RelevanceGuard (pure Python)
                try:
                    evidence_tests = getattr(ctx.deps, 'evidence_critical_tests', None)
                    if evidence_tests and isinstance(evidence_tests, list) and len(evidence_tests) > 0:
                        if not self.evaluator_agent:
                            logger.warning("Evidence-critical tests present but evaluator_agent is not available - skipping gating")
                        else:
                            # Run RelevanceGuard to classify tests
                            try:
                                cfg = load_config_from_env()
                            except Exception:
                                cfg = None
                            # Prefer ctx.deps.question if present, else empty
                            deps_question = getattr(ctx.deps, 'question', '') or ''
                            classification = classify_tests(
                                question=deps_question,
                                sql=sql,
                                tests=evidence_tests,
                                cfg=cfg,
                                langs=(getattr(ctx.deps, 'question_language', ''), getattr(ctx.deps, 'db_language', '')),
                            )
                            strict_tests = classification.get('strict', [])
                            weak_tests = classification.get('weak', [])
                            irrelevant_tests = classification.get('irrelevant', [])
                            # Log counts and a THOTHLOG line for streaming visibility
                            log_info(
                                f"THOTHLOG:RelevanceGuard pre-selection → STRICT={len(strict_tests)}, WEAK={len(weak_tests)}, IRRELEVANT={len(irrelevant_tests)}"
                            )
                            # Evaluate ONLY strict tests (blocking); declass others to non-blocking
                            if strict_tests:
                                unit_tests_str = "\n".join([f"{i}. {t}" for i, t in enumerate(strict_tests, 1)])
                                template = TemplateLoader.format(
                                    'template_evaluate_single.txt',
                                    safe=True,
                                    SQL_QUERY=sql,
                                    UNIT_TESTS=unit_tests_str
                                )
                                # Run evaluator with a strict timeout and low temperature
                                try:
                                    result = await asyncio.wait_for(
                                        self.evaluator_agent.run(
                                            template,
                                            model_settings=ModelSettings(temperature=0.2),
                                            deps=EvaluatorDeps()
                                        ),
                                        timeout=7
                                    )
                                except asyncio.TimeoutError:
                                    ctx.deps.last_execution_error = "Evidence-critical gating timed out"
                                    self._raise_model_retry(
                                        ctx,
                                        ErrorCategory.EVIDENCE_MISMATCH,
                                        sql=sql,
                                        error_message="Evidence-critical checks timed out.",
                                        additional_hints=[
                                            "Ensure the SQL is concise so evaluator can respond within timeout",
                                            "Review STRICT requirements and encode them directly in the query",
                                        ],
                                    )
                                # Extract answers
                                answers = []
                                if result and hasattr(result, 'output'):
                                    answers = getattr(result.output, 'answers', []) or []
                                # Ensure we have exactly one answer per test
                                if len(answers) != len(strict_tests):
                                    # Pad with KO for incomplete evaluation
                                    while len(answers) < len(strict_tests):
                                        answers.append(f"Test #{len(answers)+1}: KO - incomplete evaluation")
                                    answers = answers[:len(strict_tests)]
                                # Determine failures
                                def _is_ok(line: str) -> bool:
                                    if not isinstance(line, str):
                                        return False
                                    if ": " in line:
                                        return line.split(": ", 1)[1].strip().upper() == "OK"
                                    return False
                                failing = [(idx+1, ans) for idx, ans in enumerate(answers) if not _is_ok(ans)]
                                passed = len(answers) - len(failing)
                                validation_payload = [
                                    {
                                        "name": f"Test {idx+1}",
                                        "passed": _is_ok(ans),
                                        "error": ans,
                                    }
                                    for idx, ans in enumerate(answers)
                                ]
                                # Emit THOTHLOG via dual logger for observability
                                log_info(
                                    f"THOTHLOG:STRICT gating evaluated {len(answers)} strict tests: {passed} OK, {len(failing)} KO"
                                )
                                # Apply STRICT_FAILS_REQUIRED policy (default 1, recommended 2)
                                try:
                                    fails_required = int(os.getenv('STRICT_FAILS_REQUIRED', '1'))
                                except Exception:
                                    fails_required = 1
                                if len(failing) >= max(1, fails_required):
                                    reasons = "; ".join([f"Test {num}: {ans}" for num, ans in failing[:3]])
                                    ctx.deps.last_execution_error = f"Evidence-critical checks failed: {reasons}"
                                    failed_descriptions = [f"Test {num}: {ans}" for num, ans in failing]
                                    self._raise_model_retry(
                                        ctx,
                                        ErrorCategory.EVIDENCE_MISMATCH,
                                        sql=sql,
                                        error_message="Strict evidence-derived requirements were not satisfied.",
                                        validation_results=validation_payload,
                                        failed_tests=failed_descriptions,
                                        evidence_summary={
                                            "strict": len(strict_tests),
                                            "weak": len(weak_tests),
                                            "irrelevant": len(irrelevant_tests),
                                        },
                                        additional_hints=[
                                            "Incorporate each STRICT requirement explicitly in the WHERE or HAVING clause",
                                            "Preserve logical conditions while adjusting aggregations",
                                            "Re-run the mental checks against provided evidence before submitting",
                                        ],
                                    )
                            else:
                                logger.info("No STRICT tests after RelevanceGuard; skipping blocking gating evaluation")
                except ModelRetry:
                    raise
                except Exception as e:
                    logger.error(f"Error during evidence-critical gating: {e}")
                    # Be conservative: do not block on gating internal errors; proceed to next checks
                    pass
                
                # Step 5: Check for empty results if configured and dbmanager is available
                if ctx.deps.treat_empty_result_as_error and self.dbmanager:
                    logger.debug(f"Step 4: treat_empty_result_as_error=True, checking for empty results")
                    try:
                        # Execute the actual SQL to check for empty results
                        result = self.dbmanager.execute_sql(sql=sql, params={})
                        empty_result_error = self._is_empty_result(result)
                    except Exception as e:
                        logger.error(f"Error checking for empty results: {e}")
                        # Don't fail on this check, just log it
                        empty_result_error = False

                    if empty_result_error:
                        logger.debug("Empty result detected with treat_empty_result_as_error=True - triggering ModelRetry")
                        log_info("Empty result detected - ModelRetry will be triggered for retry with additional context")

                        available_tables: Optional[List[str]] = None
                        if ctx.deps.db_schema_str:
                            try:
                                available_tables = [
                                    line.strip()
                                    for line in ctx.deps.db_schema_str.splitlines()
                                    if line.strip()
                                ][:10]
                            except Exception:  # pragma: no cover - defensive parsing
                                available_tables = None

                        self._raise_model_retry(
                            ctx,
                            ErrorCategory.EMPTY_RESULT,
                            sql=sql,
                            error_message="The query executed successfully but returned no rows.",
                            available_tables=available_tables,
                        )
                elif ctx.deps.treat_empty_result_as_error and not self.dbmanager:
                    logger.warning("treat_empty_result_as_error=True but dbmanager not available - cannot check")
                else:
                    logger.debug(f"Step 5: treat_empty_result_as_error=False: Skipping empty result check")
                
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

                log_info("SQL execution exception - ModelRetry will be triggered with error details")

                logger.error("SQL validation failed - SQL was saved to state but marked as failed")
                self._raise_model_retry(
                    ctx,
                    ErrorCategory.EXECUTION_ERROR,
                    sql=failed_sql,
                    error_message=f"SQL execution failed: {str(e)}",
                    exception=e,
                )
        return validate_sql_creation
    
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
