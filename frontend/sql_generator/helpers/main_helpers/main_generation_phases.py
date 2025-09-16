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
Generation phases helper for SQL Generator.

This module contains the SQL generation and evaluation phases of the pipeline:
- SQL candidate generation
- Test generation and evaluation
- SQL selection
"""

import json
import os
import logging
from typing import TYPE_CHECKING
from datetime import datetime

from fastapi import Request

from model.system_state import SystemState
from helpers.dual_logger import log_error
from helpers.main_helpers.main_sql_generation import generate_sql_units, clean_sql_results

if TYPE_CHECKING:
    from main import GenerateSQLRequest

logger = logging.getLogger(__name__)


def _finalize_execution_state_status(state, success: bool, selected_sql: str, selection_metrics: dict, evaluation_threshold: float) -> None:
    """
    Finalize ExecutionState status based on SQL selection results.
    
    Args:
        state: SystemState containing execution context
        success: Whether SQL selection was successful
        selected_sql: The selected SQL query (if any)
        selection_metrics: Metrics from SQL selection
        evaluation_threshold: Threshold for SILVER status
    """
    if not success:
        # SQL selection failed - set to FAILED status
        state.execution.sql_status = "FAILED"
        if hasattr(state.execution, 'evaluation_case') and state.execution.evaluation_case:
            # Update case to reflect failure if not already D-FAILED
            if not state.execution.evaluation_case.endswith("-FAILED"):
                case_letter = state.execution.evaluation_case.split("-")[0] if "-" in state.execution.evaluation_case else "D"
                state.execution.evaluation_case = f"{case_letter}-FAILED"
        else:
            state.execution.evaluation_case = "D-FAILED"
        
        logger.info(f"Finalized ExecutionState status: {state.execution.sql_status}, case: {state.execution.evaluation_case}")
        return
    
    if not selected_sql:
        # Should not happen with success=True, but handle gracefully
        state.execution.sql_status = "FAILED" 
        state.execution.evaluation_case = "D-FAILED"
        logger.warning("SQL selection reported success but no SQL was selected")
        return
    
    # SQL selection was successful - determine final status from selection_metrics
    try:
        # Get selection reason to understand the quality
        selection_reason = selection_metrics.get('selection_reason', '').lower()
        final_status = selection_metrics.get('final_status', '').upper()
        
        # Check if this is enhanced evaluation with explicit status
        if final_status in ['GOLD', 'SILVER', 'FAILED']:
            state.execution.sql_status = final_status
        else:
            # Determine status from selection reason keywords
            if any(keyword in selection_reason for keyword in ['perfect', '100%', 'all tests pass', 'gold']):
                state.execution.sql_status = "GOLD"
            elif any(keyword in selection_reason for keyword in ['above threshold', f'{evaluation_threshold}%', 'silver']):
                state.execution.sql_status = "SILVER"
            elif any(keyword in selection_reason for keyword in ['below threshold', 'low confidence', 'failed']):
                state.execution.sql_status = "FAILED"
            else:
                # Default to SILVER for successful selection if unclear
                state.execution.sql_status = "SILVER"
        
        # Update evaluation_case to reflect final status if needed
        if hasattr(state.execution, 'evaluation_case') and state.execution.evaluation_case:
            current_case = state.execution.evaluation_case
            if "-" in current_case:
                case_letter, old_status = current_case.split("-", 1)
                
                # IMPORTANT: Do not downgrade status from GOLD to SILVER or SILVER to FAILED
                # If evaluation already determined a higher status, preserve it
                status_hierarchy = {"GOLD": 3, "SILVER": 2, "FAILED": 1}
                old_status_level = status_hierarchy.get(old_status, 0)
                new_status_level = status_hierarchy.get(state.execution.sql_status, 0)
                
                # Only update if the new status is higher than the old status
                if new_status_level > old_status_level:
                    state.execution.evaluation_case = f"{case_letter}-{state.execution.sql_status}"
                    logger.info(f"Upgraded evaluation case from {current_case} to {state.execution.evaluation_case}")
                elif old_status_level > new_status_level:
                    # Keep the higher status from evaluation, update sql_status to match
                    state.execution.sql_status = old_status
                    logger.info(f"Preserved higher evaluation status: {current_case}, adjusted sql_status to {old_status}")
                # If equal, keep current case unchanged
            else:
                # Add status suffix if missing
                state.execution.evaluation_case = f"{current_case}-{state.execution.sql_status}"
        else:
            # Set default case if missing  
            state.execution.evaluation_case = f"A-{state.execution.sql_status}"
        
        # Store complexity information if available
        selected_sql_index = selection_metrics.get('selected_sql_index', 0)
        if isinstance(selected_sql_index, int) and selected_sql_index >= 0:
            # Could calculate complexity score here if needed
            state.execution.selected_sql_complexity = 1.0 - (selected_sql_index / max(1, len(state.generated_sqls)))
        
        logger.info(f"Finalized ExecutionState status: {state.execution.sql_status}, case: {state.execution.evaluation_case}")
        
    except Exception as e:
        logger.error(f"Error finalizing ExecutionState status: {e}", exc_info=True)
        # Set safe fallback values
        state.execution.sql_status = "SILVER"  # Assume silver since selection was successful
        if hasattr(state.execution, 'evaluation_case') and state.execution.evaluation_case:
            case_letter = state.execution.evaluation_case.split("-")[0] if "-" in state.execution.evaluation_case else "A"
            state.execution.evaluation_case = f"{case_letter}-SILVER"
        else:
            state.execution.evaluation_case = "A-SILVER"


async def _precompute_tests_phase(
    state: SystemState,
    request: "GenerateSQLRequest",
    http_request: Request
):
    """
    Precompute validation tests BEFORE SQL generation.
    - Generates tests based on question, schema, and evidence (no SQL candidates yet)
    - Deduplicates tests and stores them in state (filtered_tests)
    - Enables stateless evidence-critical gating during SQL generation
    """
    # Early disconnect check
    if await http_request.is_disconnected():
        logger.info("Client disconnected before precompute tests phase")
        yield "CANCELLED:Operation cancelled by user\n"
        return

    # Inform the client
    yield f"THOTHLOG:Precomputing {state.number_of_tests_to_generate} validation tests from Evidence and Schema\n"

    try:
        # Lazy import to avoid cycles
        from helpers.main_helpers.main_test_generation import generate_test_units

        test_result_list = await generate_test_units(state, state.agents_and_tools, request.functionality_level)

        if not test_result_list:
            yield "THOTHLOG:No tests were generated in precompute phase\n"
            return

        # Save full results
        state.generated_tests = test_result_list
        state.generated_tests_json = json.dumps(state.generated_tests, ensure_ascii=True)

        # Deduplicate across all answers while preserving order
        seen = set()
        unique_tests = []
        for _, answers in test_result_list:
            if not answers:
                continue
            for a in answers:
                if a and a != "GENERATION FAILED" and a not in seen:
                    seen.add(a)
                    unique_tests.append(a)

        # Store filtered tests for downstream use
        if hasattr(state, 'filtered_tests'):
            state.filtered_tests = unique_tests
        if hasattr(state, 'filtered_tests_json'):
            try:
                state.filtered_tests_json = json.dumps(unique_tests, ensure_ascii=True)
            except Exception:
                pass

        # Count evidence-critical tests
        ev_crit_count = sum(1 for t in unique_tests if isinstance(t, str) and "[EVIDENCE-CRITICAL]" in t)
        yield f"THOTHLOG:Precompute tests ready: {len(unique_tests)} tests ({ev_crit_count} evidence-critical)\n"

    except Exception as e:
        log_error(f"Error in precompute tests phase: {type(e).__name__}: {str(e)}")
        yield f"THOTHLOG:Warning: Precompute tests failed: {str(e)}\n"


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
    
    # Inform about evidence-critical gating status before generation
    try:
        ev_crit_count = 0
        if hasattr(state, 'filtered_tests') and state.filtered_tests:
            ev_crit_count = sum(1 for t in state.filtered_tests if isinstance(t, str) and "[EVIDENCE-CRITICAL]" in t)
        elif hasattr(state, 'generated_tests') and state.generated_tests:
            for _, answers in state.generated_tests:
                if not answers:
                    continue
                ev_crit_count += sum(1 for t in answers if isinstance(t, str) and "[EVIDENCE-CRITICAL]" in t)
        if ev_crit_count > 0:
            yield f"THOTHLOG:Evidence-critical gating enabled with {ev_crit_count} mandatory tests\n"
        else:
            yield f"THOTHLOG:No evidence-critical gating (no evidence-derived rules detected)\n"
    except Exception:
        # Non-fatal
        pass
    
    # Generate sqls in parallel
    yield f"THOTHLOG:Generating {state.number_of_sql_to_generate} SQL in parallel\n"  
    
    # Set SQL generation start time
    state.execution.sql_generation_start_time = datetime.now()
    
    try:
        sql_results = await generate_sql_units(state, state.agents_and_tools, request.functionality_level)
        
        # Set SQL generation end time and calculate duration
        state.execution.sql_generation_end_time = datetime.now()
        if state.execution.sql_generation_start_time and state.execution.sql_generation_end_time:
            duration = (state.execution.sql_generation_end_time - state.execution.sql_generation_start_time).total_seconds() * 1000
            state.execution.sql_generation_duration_ms = duration
            
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
    
    # Check for critical database error
    if sql_results and len(sql_results) == 1 and sql_results[0].startswith("CRITICAL_DATABASE_ERROR:"):
        error_message = sql_results[0].replace("CRITICAL_DATABASE_ERROR: ", "")
        log_error(f"Critical database error detected: {error_message}")
        
        # Store the error in state for backend logging
        state.execution.sql_generation_failure_message = f"Database unavailable: {error_message}"
        state.execution.sql_status = "DATABASE_ERROR"
        
        error_msg = {
            "type": "database_error",
            "component": "sql_generation",
            "message": "Database is unavailable or corrupted",
            "details": error_message,
            "impact": "Cannot access database to generate SQL",
            "action": "Please check database availability and try again"
        }
        yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
        yield f"ERROR: Database unavailable - {error_message}\n"
        # Don't return here - let it continue to log the error to backend
        sql_results = []  # Clear results to trigger the no SQL generated path
    
    # Critical check: at least one SQL must be generated
    if not sql_results or len(sql_results) == 0:
        error_details = {
            "workspace_id": request.workspace_id,
            "question": state.question,
            "functionality_level": request.functionality_level,
            "schema_strategy": state.schema_link_strategy if hasattr(state, 'schema_link_strategy') else None
        }
        # Format message to avoid Logfire interpreting JSON braces as placeholders
        log_error(
            f"Critical: No SQL statements generated - workspace_id={request.workspace_id}, "
            f"question='{state.question[:100] if state.question else 'N/A'}...', "
            f"functionality_level={request.functionality_level}, "
            f"schema_strategy={state.schema_link_strategy if hasattr(state, 'schema_link_strategy') else 'None'}"
        )
        
        # If we previously detected a database error, do not escalate
        if getattr(state.execution, 'sql_status', '') == 'DATABASE_ERROR':
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

        # Try escalation to next functionality level (BASIC -> ADVANCED -> EXPERT)
        from helpers.main_helpers.escalation_manager import EscalationManager, EscalationContext, EscalationReason
        from model.generator_type import GeneratorType

        current_level = GeneratorType.from_string(request.functionality_level)
        next_level = EscalationManager.get_next_level(current_level)

        # Initialize escalation attempts if not present
        if not hasattr(state, 'escalation_attempts'):
            state.escalation_attempts = 0

        if next_level and state.escalation_attempts < 2:  # Max 2 escalations (BASIC->ADVANCED->EXPERT)
            # Emit escalation log
            if next_level.name == "ADVANCED":
                yield f"THOTHLOG:Escalation to Advanced Agent\n"
            elif next_level.name == "EXPERT":
                yield f"THOTHLOG:Escalation to Expert Agent\n"
            else:
                yield f"THOTHLOG:Escalating to {next_level.display_name} agent\n"
            logger.info(f"Escalating SQL generation (no SQL) from {current_level.name} to {next_level.name}")

            # Build escalation context
            escalation_context = EscalationContext(
                reason=EscalationReason.NO_SQL_GENERATED,
                current_level=current_level,
                question=state.question,
                failed_sqls=getattr(state, 'generated_sqls', []) if hasattr(state, 'generated_sqls') else [],
                evaluation_results={"cause": "no_sql_generated"},
                failure_analysis="No SQL candidates were generated at this level"
            )

            # Update state for escalation
            state.escalation_attempts += 1
            state.escalation_context = escalation_context.to_context_string()

            try:
                EscalationManager.update_state_for_escalation(state, next_level, escalation_context)
            except Exception as e:
                # Guard against state mutation errors during streaming
                log_error(f"Escalation state update failed: {type(e).__name__}: {str(e)}")
                error_msg = {
                    "type": "critical_error",
                    "component": "escalation",
                    "message": "Escalation failed due to state update error",
                    "details": str(e),
                    "impact": "Cannot continue with higher-level agents",
                    "action": "Please check SystemState mutability and escalation manager"
                }
                yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
                yield f"ERROR: Escalation failed - {str(e)}\n"
                return

            # Update request level (uppercase expected by validator)
            request.functionality_level = next_level.name

            # Clear previous generation results
            state.generated_sqls = []
            if hasattr(state, 'generated_tests'):
                state.generated_tests = []
            if hasattr(state, 'evaluation_results'):
                state.evaluation_results = []

            yield f"THOTHLOG:Starting new SQL generation attempt with {next_level.display_name} agents\n"

            # Recursively call generation phase at the higher level
            async for result in _generate_sql_candidates_phase(state, request, http_request):
                if isinstance(result, str):
                    yield result
            return
        else:
            # Cannot escalate further or attempts exhausted
            if not next_level:
                logger.info("Already at maximum functionality level (EXPERT), cannot escalate further")
                yield f"THOTHLOG:Maximum functionality level reached - cannot escalate beyond {current_level.display_name}\n"
            else:
                logger.info(f"Maximum escalation attempts ({state.escalation_attempts}) reached")
                yield f"THOTHLOG:Maximum escalation attempts reached - stopping after {state.escalation_attempts} escalations\n"

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
    # Optional dev bypass: skip test generation/evaluation entirely
    try:
        bypass_eval = os.getenv('SQLGEN_BYPASS_EVALUATION', 'false').lower() == 'true'
    except Exception:
        bypass_eval = False

    if bypass_eval:
        # Ensure we have at least one generated SQL to select
        if hasattr(state, 'generated_sqls') and state.generated_sqls:
            selected_sql = state.generated_sqls[0]
            # Mark selection in state for downstream phases/logging
            state.last_SQL = selected_sql
            selection_metrics = {
                "total_sqls": len(state.generated_sqls),
                "evaluation_threshold": 0,
                "sql_scores": [],
                "finalists": [],
                "selection_reason": "Evaluation bypassed by SQLGEN_BYPASS_EVALUATION=true",
                "selected_sql_index": 0,
                "final_status": "SILVER"
            }
            # Finalize execution status and emit logs
            _finalize_execution_state_status(state, True, selected_sql, selection_metrics, 0)
            yield "THOTHLOG:Evaluation bypassed by configuration; selecting first SQL candidate\n"
            yield ("RESULT", True, selected_sql)
            return
        else:
            # No SQLs available to bypass-select; fall through to normal error path
            yield "THOTHLOG:Evaluation bypass requested but no SQL candidates available\n"

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
    
    # Count evidence-critical tests for observability
    try:
        ev_crit_count = 0
        if hasattr(state, 'filtered_tests') and state.filtered_tests:
            ev_crit_count = sum(1 for t in state.filtered_tests if isinstance(t, str) and "[EVIDENCE-CRITICAL]" in t)
        else:
            for _, answers in state.generated_tests:
                if not answers:
                    continue
                ev_crit_count += sum(1 for t in answers if isinstance(t, str) and "[EVIDENCE-CRITICAL]" in t)
        yield f"THOTHLOG:Evaluating SQL candidates with {unique_test_count} unique tests (deduplicated from {len(state.generated_tests)} test sets; {ev_crit_count} evidence-critical)\n"
    except Exception:
        yield f"THOTHLOG:Evaluating SQL candidates with {unique_test_count} unique tests (deduplicated from {len(state.generated_tests)} test sets)\n"
    
    # Get evaluation threshold from workspace
    evaluation_threshold = state.workspace.get('evaluation_threshold', 90)
    logger.debug(f"Using evaluation threshold: {evaluation_threshold}%")
    
    from helpers.main_helpers.main_evaluation import evaluate_sql_candidates, populate_execution_state_from_evaluation
    
    # Record evaluation start time
    if hasattr(state, 'execution'):
        state.execution.evaluation_start_time = datetime.now()
    
    # Run standard evaluation flow
    evaluation_result = await evaluate_sql_candidates(state, state.agents_and_tools)
    
    # Record evaluation end time
    if hasattr(state, 'execution') and state.execution.evaluation_start_time:
        state.execution.evaluation_end_time = datetime.now()
        state.execution.evaluation_duration_ms = (state.execution.evaluation_end_time - state.execution.evaluation_start_time).total_seconds() * 1000
    
    # Store evaluation results in state
    state.evaluation_results = evaluation_result
    state.evaluation_results_json = json.dumps(evaluation_result, ensure_ascii=True)
    
    # Populate ExecutionState fields for ThothLog
    populate_execution_state_from_evaluation(state, evaluation_result, evaluation_threshold)
    
    # Extract thinking and answers for compatibility
    if evaluation_result and len(evaluation_result) > 0:
        thinking_str, answers_list = evaluation_result[0]
        state.enhanced_evaluation_result = (thinking_str, answers_list)
        
        # Set default values for enhanced evaluation metadata
        state.enhanced_evaluation_status = "COMPLETED"
        state.enhanced_evaluation_selected_sql = None
        state.enhanced_evaluation_case = "STANDARD_EVALUATION"
        state.enhanced_evaluation_selected_sql_index = None
        state.evaluation_logs = json.dumps({"evaluation_type": "standard", "test_count": len(answers_list) if answers_list else 0}, ensure_ascii=False)
    else:
        # Handle empty evaluation results
        state.enhanced_evaluation_result = ("No evaluation results", [])
        state.enhanced_evaluation_status = "FAILED"
        state.enhanced_evaluation_selected_sql = None
        state.enhanced_evaluation_case = "NO_RESULTS"
        state.enhanced_evaluation_selected_sql_index = None
        state.evaluation_logs = json.dumps({"evaluation_type": "standard", "error": "no_results"}, ensure_ascii=False)
    
    # evaluation_result is now a list of tuples [(thinking, answers)]
    if evaluation_result and len(evaluation_result) > 0:
        logger.debug(f"Evaluation complete: thinking length={len(evaluation_result[0][0])}, verdicts={len(evaluation_result[0][1])}")
    
    # If filtered tests are available, override generated_tests_json with them for backend
    if hasattr(state, 'filtered_tests') and state.filtered_tests:
        logger.info(f"Using {len(state.filtered_tests)} filtered tests for backend logging")
        # Save filtered tests as simple list for the backend
        state.generated_tests_json = json.dumps(state.filtered_tests, ensure_ascii=False)

    # SQLite 3.30.0+ (October 2019) supports NULLS LAST/FIRST, so templates now handle this correctly for all databases
    from helpers.main_helpers.sql_selection import select_best_sql
    
    # Record SQL selection start time
    if hasattr(state, 'execution'):
        state.execution.sql_selection_start_time = datetime.now()
    
    # Use original SQLs and evaluation results without "fixing"
    fixed_sqls = state.generated_sqls
    fixed_evaluation_results = state.evaluation_results
    
    # Update state with fixed SQLs and evaluation results
    state.generated_sqls = fixed_sqls
    state.evaluation_results = fixed_evaluation_results
    state.evaluation_results_json = json.dumps(fixed_evaluation_results, ensure_ascii=True)
    logger.debug("Applied small bug fixes to SQL queries")
    
    # Check if enhanced evaluation already selected a SQL
    if (hasattr(state, 'enhanced_evaluation_status') and state.enhanced_evaluation_status and
        hasattr(state, 'enhanced_evaluation_selected_sql') and state.enhanced_evaluation_selected_sql):
        
        if state.enhanced_evaluation_status == 'GOLD' and state.enhanced_evaluation_selected_sql:
            # Enhanced evaluation already selected the best SQL
            success = True
            selected_sql = state.enhanced_evaluation_selected_sql
            error_message = None
            
            # Create selection metrics compatible with existing code
            selection_metrics = {
                'total_sqls': len(state.generated_sqls),
                'evaluation_threshold': evaluation_threshold,
                'selection_reason': f"Enhanced evaluation Case {state.enhanced_evaluation_case}: {state.enhanced_evaluation_result[0][:100] if state.enhanced_evaluation_result else 'N/A'}...",
                'selected_sql_index': state.enhanced_evaluation_selected_sql_index or 0,
                'auxiliary_agents_used': [],  # This info would need to be stored separately if needed
                'processing_time_ms': 0,  # This info would need to be stored separately if needed
                'evaluation_type': 'enhanced',  # Mark this as enhanced evaluation
                'final_status': 'GOLD',  # Mark status as GOLD for enhanced evaluation success
                'finalists': [{'sql_index': state.enhanced_evaluation_selected_sql_index or 0}],  # Include finalist info
                'sql_scores': []  # Empty for enhanced evaluation since we don't have traditional test scores
            }
            
            logger.info(f"Enhanced evaluation selected SQL via Case {state.enhanced_evaluation_case}")
        else:
            # Enhanced evaluation failed, fall back to legacy selection
            logger.warning(f"Enhanced evaluation failed with status {state.enhanced_evaluation_status}, falling back to legacy selection")
            
            from helpers.main_helpers.sql_selection import select_best_sql
            success, selected_sql, error_message, selection_metrics = await select_best_sql(
                state.generated_sqls,
                state.evaluation_results,
                evaluation_threshold=evaluation_threshold,
                state=state,
                agents_and_tools=state.agents_and_tools
            )
    else:
        # Fallback to legacy selection if enhanced evaluation not available
        logger.warning("Enhanced evaluation result not available, using legacy selection")
        
        from helpers.main_helpers.sql_selection import select_best_sql
        success, selected_sql, error_message, selection_metrics = await select_best_sql(
            state.generated_sqls,
            state.evaluation_results,
            evaluation_threshold=evaluation_threshold,
            state=state,
            agents_and_tools=state.agents_and_tools
        )
    
    # Save selection metrics
    state.selection_metrics = selection_metrics
    state.selection_metrics_json = json.dumps(selection_metrics, ensure_ascii=True)
    
    # Record SQL selection end time
    if hasattr(state, 'execution') and state.execution.sql_selection_start_time:
        state.execution.sql_selection_end_time = datetime.now()
        state.execution.sql_selection_duration_ms = (state.execution.sql_selection_end_time - state.execution.sql_selection_start_time).total_seconds() * 1000
    
    # Finalize ExecutionState status based on SQL selection results
    _finalize_execution_state_status(state, success, selected_sql, selection_metrics, evaluation_threshold)
    
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
        
        # NOTE: No error messages sent to frontend - only THOTHLOG messages
        # The failure information is preserved in state for Django logging
        
        # Check if we should escalate to a higher functionality level
        from helpers.main_helpers.escalation_manager import EscalationManager, EscalationContext, EscalationReason
        from model.generator_type import GeneratorType
        
        current_level = GeneratorType.from_string(request.functionality_level)
        next_level = EscalationManager.get_next_level(current_level)
        
        # Initialize escalation attempts if not present
        if not hasattr(state, 'escalation_attempts'):
            state.escalation_attempts = 0
        
        # Check if we can and should escalate
        if next_level and state.escalation_attempts < 2:  # Max 2 escalations (BASIC->ADVANCED->EXPERT)
            if next_level.name == "ADVANCED":
                yield f"THOTHLOG:Escalation to Advanced Agent\n"
            elif next_level.name == "EXPERT":
                yield f"THOTHLOG:Escalation to Expert Agent\n"
            else:
                yield f"THOTHLOG:Escalating to {next_level.display_name} agent\n"  # generic fallback
            logger.info(f"Escalating SQL generation from {current_level.name} to {next_level.name}")
            
            # Create escalation context
            escalation_context = EscalationContext(
                reason=EscalationReason.ALL_FAILED_EVALUATION,
                current_level=current_level,
                question=state.question,
                failed_sqls=state.generated_sqls if hasattr(state, 'generated_sqls') else [],
                evaluation_results=selection_metrics,
                failure_analysis=error_message
            )
            
            # Update state for escalation
            state.escalation_attempts += 1
            state.escalation_context = escalation_context.to_context_string()
            
            # Update escalation flags using EscalationManager
            try:
                EscalationManager.update_state_for_escalation(state, next_level, escalation_context)
            except Exception as e:
                # Guard against state mutation errors during streaming
                log_error(f"Escalation state update failed: {type(e).__name__}: {str(e)}")
                error_msg = {
                    "type": "critical_error",
                    "component": "escalation",
                    "message": "Escalation failed due to state update error",
                    "details": str(e),
                    "impact": "Cannot continue with higher-level agents",
                    "action": "Please check SystemState mutability and escalation manager"
                }
                yield f"CRITICAL_ERROR:{json.dumps(error_msg, ensure_ascii=True)}\n"
                yield f"ERROR: Escalation failed - {str(e)}\n"
                return
            
            # Update request with new functionality level (uppercase expected by validator)
            request.functionality_level = next_level.name
            
            # Clear previous generation results to start fresh
            state.generated_sqls = []
            state.generated_tests = []
            state.evaluation_results = []
            
            yield f"THOTHLOG:Starting new SQL generation attempt with {next_level.display_name} agents\n"
            
            # Recursively call the generation phases with the escalated level
            # First regenerate SQL candidates
            async for result in _generate_sql_candidates_phase(state, request, http_request):
                if isinstance(result, str):
                    yield result
            
            # Then evaluate and select
            async for result in _evaluate_and_select_phase(state, request, http_request):
                if isinstance(result, tuple) and result[0] == "RESULT":
                    # Return the escalated result
                    yield result
                    return
                else:
                    yield result
            return
        else:
            if not next_level:
                logger.info("Already at maximum functionality level (EXPERT), cannot escalate further")
                yield f"THOTHLOG:Maximum functionality level reached - cannot escalate beyond {current_level.display_name}\n"
            else:
                logger.info(f"Maximum escalation attempts ({state.escalation_attempts}) reached")
                yield f"THOTHLOG:Maximum escalation attempts reached - stopping after {state.escalation_attempts} escalations\n"
        
        # Don't return here - we need to continue to send the log to Django
    
    # Yield the results as tuple for the orchestrator  
    yield ("RESULT", success, selected_sql)
