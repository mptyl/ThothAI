# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Generation phases helper for SQL Generator.

This module contains the SQL generation and evaluation phases of the pipeline:
- SQL candidate generation
- Test generation and evaluation
- SQL selection
"""

import json
import logging
from typing import TYPE_CHECKING

from fastapi import Request

from model.system_state import SystemState
from helpers.dual_logger import log_error
from helpers.main_helpers.main_sql_generation import generate_sql_units, clean_sql_results

if TYPE_CHECKING:
    from main import GenerateSQLRequest

logger = logging.getLogger(__name__)


async def _generate_sql_candidates_phase(
    state: SystemState,
    request: "GenerateSQLRequest",
    http_request: Request
):
    """
    Generate SQL candidates using the configured agents.
    
    Args:
        state: The system state
        request: The SQL generation request
        http_request: The HTTP request object
        
    Yields:
        Progress messages to client
    """
    # Check for client disconnection before SQL generation (CRITICAL - longest operation)
    if await http_request.is_disconnected():
        logger.info("Client disconnected before SQL generation")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    # Generate sqls in parallel
    yield f"THOTHLOG:Generating {state.number_of_sql_to_generate} SQL in parallel\n"  
    try:
        sql_results = await generate_sql_units(state, state.agents_and_tools, request.functionality_level)
    except Exception as e:
        error_details = {
            "workspace_id": request.workspace_id,
            "functionality_level": request.functionality_level,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        log_error(f"Critical failure in SQL generation: {json.dumps(error_details)}")
        
        error_msg = {
            "type": "critical_error",
            "component": "sql_generation",
            "message": "Failed to generate SQL statements",
            "details": str(e),
            "impact": "Cannot proceed without SQL generation",
            "action": "Please check agent configuration and model availability"
        }
        yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
        yield f"ERROR: SQL generation failed - {str(e)}\n"
        return

    # Clean the generated SQL results
    sql_results = clean_sql_results(sql_results)
    
    # Critical check: at least one SQL must be generated
    if not sql_results or len(sql_results) == 0:
        error_details = {
            "workspace_id": request.workspace_id,
            "question": state.question,
            "functionality_level": request.functionality_level,
            "schema_strategy": state.schema_link_strategy if hasattr(state, 'schema_link_strategy') else None
        }
        log_error(f"Critical: No SQL statements generated: {json.dumps(error_details)}")
        
        error_msg = {
            "type": "critical_error",
            "component": "sql_generation",
            "message": "No valid SQL statements were generated",
            "details": "All SQL generation attempts failed or produced invalid results",
            "impact": "Cannot proceed without at least one valid SQL statement",
            "action": "Please check: 1) Question clarity, 2) Database schema availability, 3) Agent configuration"
        }
        yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
        yield "ERROR: No SQL statements could be generated for your question\n"
        return
    
    yield f"THOTHLOG:Cleaned SQL results - {len(sql_results)} unique valid SQL statements\n"
    state.generated_sqls = sql_results
    state.generated_sqls_json = json.dumps(state.generated_sqls, ensure_ascii=True)


async def _evaluate_and_select_phase(
    state: SystemState,
    request: "GenerateSQLRequest",
    http_request: Request
):
    """
    Generate validation tests, evaluate SQL candidates, and select the best one.
    
    Args:
        state: System state with SQL candidates
        request: The original SQL generation request
        http_request: HTTP request for checking disconnection
        
    Yields:
        Progress messages to client and final result tuple
    """
    # Check for client disconnection before test generation
    if await http_request.is_disconnected():
        logger.info("Client disconnected before test generation")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    # Generate tests in parallel
    yield f"THOTHLOG:Generating {state.number_of_tests_to_generate} validation tests in parallel\n"
    from helpers.main_helpers.main_test_generation import generate_test_units
    
    try:
        test_result_list = await generate_test_units(state, state.agents_and_tools, request.functionality_level)
    except Exception as e:
        error_details = {
            "workspace_id": request.workspace_id,
            "num_sqls": len(state.generated_sqls) if hasattr(state, 'generated_sqls') else 0,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        log_error(f"Critical failure in test generation: {json.dumps(error_details)}")
        
        error_msg = {
            "type": "critical_error",
            "component": "test_generation",
            "message": "Failed to generate validation tests",
            "details": str(e),
            "impact": "Cannot validate SQL statements without tests",
            "action": "Please check test agent configuration and model availability"
        }
        yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
        yield f"ERROR: Test generation failed - {str(e)}\n"
        return
    
    # Critical check: at least one test must be generated
    if not test_result_list or len(test_result_list) == 0:
        error_details = {
            "workspace_id": request.workspace_id,
            "num_sqls": len(state.generated_sqls) if hasattr(state, 'generated_sqls') else 0,
            "test_agent_exists": bool(getattr(state.agents_and_tools, 'test_gen_agent_1', None))
        }
        log_error(f"Critical: No tests generated: {json.dumps(error_details)}")
        
        error_msg = {
            "type": "critical_error",
            "component": "test_generation",
            "message": "No validation tests were generated",
            "details": "All test generation attempts failed",
            "impact": "Cannot validate SQL statements without tests",
            "action": "Please check test agent configuration in workspace settings"
        }
        yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
        yield "ERROR: No validation tests could be generated\n"
        return
    
    # Save test results to state
    state.generated_tests = test_result_list
    state.generated_tests_json = json.dumps(state.generated_tests, ensure_ascii=True)
    logger.debug(f"Generated tests: {len(state.generated_tests)} tests")
    
    # Count unique tests for logging
    all_test_answers = []
    for _, answers in state.generated_tests:
        all_test_answers.extend(answers)
    unique_test_count = len(set(answer for answer in all_test_answers if answer != "GENERATION FAILED"))
    
    # Check for client disconnection before evaluation
    if await http_request.is_disconnected():
        logger.info("Client disconnected before evaluation")
        yield "CANCELLED:Operation cancelled by user\n"
        return
    
    yield f"THOTHLOG:Evaluating SQL candidates with {unique_test_count} unique tests (deduplicated from {len(state.generated_tests)} test sets)\n"
    from helpers.main_helpers.main_evaluation import evaluate_sql_candidates
    
    # Run evaluator
    evaluation_result = await evaluate_sql_candidates(state, state.agents_and_tools)
    state.evaluation_results = evaluation_result
    state.evaluation_results_json = json.dumps(evaluation_result, ensure_ascii=True)
    
    # evaluation_result is now a list of tuples [(thinking, answers)]
    if evaluation_result and len(evaluation_result) > 0:
        logger.debug(f"Evaluation complete: thinking length={len(evaluation_result[0][0])}, verdicts={len(evaluation_result[0][1])}")

    # NOTE: Removed small_bug_fixer step - was adding NULLS LAST/FIRST that breaks SQLite
    # NULLS handling is now done conditionally in SQL generation templates
    from helpers.main_helpers.sql_selection import select_best_sql
    
    # Use original SQLs and evaluation results without "fixing"
    fixed_sqls = state.generated_sqls
    fixed_evaluation_results = state.evaluation_results
    
    # Update state with fixed SQLs and evaluation results
    state.generated_sqls = fixed_sqls
    state.evaluation_results = fixed_evaluation_results
    state.evaluation_results_json = json.dumps(fixed_evaluation_results, ensure_ascii=True)
    logger.debug("Applied small bug fixes to SQL queries")
    
    # Get evaluation threshold and select best SQL
    evaluation_threshold = state.workspace.get('evaluation_threshold', 90)
    logger.debug(f"Using evaluation threshold: {evaluation_threshold}%")
    
    success, selected_sql, error_message, selection_metrics = select_best_sql(
        state.generated_sqls,
        state.evaluation_results,
        evaluation_threshold=evaluation_threshold
    )
    
    # Save selection metrics
    state.selection_metrics = selection_metrics
    state.selection_metrics_json = json.dumps(selection_metrics, ensure_ascii=True)
    
    if success:
        if selected_sql:
            state.last_SQL = selected_sql
            state.successful_agent_name = f"Selected from {selection_metrics['total_sqls']} candidates - {selection_metrics['selection_reason']}"
            
            # Check if selection is below threshold
            if "below" in selection_metrics.get("selection_reason", "").lower():
                yield f"THOTHLOG:WARNING: SQL selected with low confidence - {selection_metrics['selection_reason']}\n"
                logger.warning(f"SQL selection with low confidence: {selection_metrics}")
                
                # Create simplified metrics for warning (without test details)
                simplified_warning_metrics = {
                    "selection_reason": selection_metrics.get("selection_reason", ""),
                    "num_sqls_evaluated": len(selection_metrics.get("sql_scores", [])) if selection_metrics else 0
                }
                warning_data = json.dumps({
                    "type": "sql_low_confidence",
                    "reason": selection_metrics['selection_reason'],
                    "metrics": simplified_warning_metrics
                }, ensure_ascii=True)
                yield f"SQL_WARNING:{warning_data}\n"
            else:
                yield f"THOTHLOG:SQL selection successful - {selection_metrics['selection_reason']}\n"
                logger.debug(f"SQL selection successful: {selection_metrics}")
        else:
            # This should not happen with the fixes, but handle it gracefully
            logger.error(f"Success reported but selected_sql is None. Metrics: {selection_metrics}")
            success = False
            error_message = "Internal error: SQL selection succeeded but no SQL was returned"
            state.sql_generation_failure_message = error_message
    else:
        # Handle selection failure
        error_details = {
            "workspace_id": request.workspace_id,
            "question": state.question,
            "num_sqls_generated": len(state.generated_sqls) if hasattr(state, 'generated_sqls') else 0,
            "selection_error": error_message,
            "selection_metrics": selection_metrics
        }
        log_error(f"Critical: SQL selection failed: {json.dumps(error_details)}")
        
        yield f"THOTHLOG:SQL selection failed - no queries passed {evaluation_threshold}% threshold\n"
        state.sql_generation_failure_message = error_message
        state.last_SQL = ""
        
        yield f"{error_message}\n"
        
        # Create a simplified metrics object for frontend (without test details)
        simplified_metrics = {
            "selection_reason": selection_metrics.get("selection_reason", ""),
            "num_sqls_evaluated": len(selection_metrics.get("sql_scores", [])) if selection_metrics else 0
        }
        failure_data = json.dumps({
            "type": "sql_generation_failed",
            "error": "SQL generation failed. Please check the logs for details.",
            "metrics": simplified_metrics
        }, ensure_ascii=True)
        yield f"SQL_GENERATION_FAILED:{failure_data}\n"
        # Don't return here - we need to continue to send the log to Django
    
    # Yield the results as tuple for the orchestrator  
    yield ("RESULT", success, selected_sql)