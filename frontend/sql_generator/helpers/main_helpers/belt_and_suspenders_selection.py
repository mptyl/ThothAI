# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

"""
Belt and Suspenders Selection module for enhanced SQL selection when evaluation 
results are borderline (cases B or C).

This module implements the SqlEvaluator agent workflow for improved SQL selection
based on failed test analysis and domain knowledge.
"""

import logging
from typing import List, Tuple, Dict, Optional, Any
from datetime import datetime
import json

from model.system_state import SystemState
from helpers.template_preparation import TemplateLoader, clean_template_for_llm
from agents.core.agent_initializer import AgentInitializer
from helpers.dual_logger import log_error

logger = logging.getLogger(__name__)


async def perform_belt_and_suspenders_selection(
    state: SystemState,
    generated_sqls: List[str],
    evaluation_results: List[Tuple[str, List[str]]],
    agents_and_tools: Any
) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """
    Perform enhanced SQL selection using SqlEvaluator agent when belt_and_suspenders is enabled.
    
    This function is called when evaluation results are borderline (cases B or C) and
    belt_and_suspenders flag is active. It uses the SqlEvaluator agent to analyze
    SQL candidates with their failed test details to make a more informed selection.
    
    Args:
        state: SystemState containing workspace and execution context
        generated_sqls: List of generated SQL queries to select from
        evaluation_results: List of tuples [(thinking, answers)] with test results
        agents_and_tools: Agent and tool configurations
        
    Returns:
        Tuple of (success, selected_sql, error_message, metrics)
        - success: True if a SQL was successfully selected
        - selected_sql: The selected SQL query or None
        - error_message: Error message if selection failed
        - metrics: Dictionary with selection metrics and timing data
    """
    logger.info("Performing Belt and Suspenders enhanced SQL selection")
    
    # Initialize timing
    start_time = datetime.now()
    
    try:
        # Extract test evaluator agent config to use same model for consistency
        test_evaluator_config = None
        if hasattr(state, 'workspace') and state.workspace and state.workspace.test_evaluator_agent:
            test_evaluator_config = {
                'name': state.workspace.test_evaluator_agent.name,
                'ai_model': state.workspace.test_evaluator_agent.ai_model,
                'temperature': state.workspace.test_evaluator_agent.temperature,
                'top_p': state.workspace.test_evaluator_agent.top_p,
                'max_tokens': state.workspace.test_evaluator_agent.max_tokens,
                'timeout': state.workspace.test_evaluator_agent.timeout,
                'retries': state.workspace.test_evaluator_agent.retries,
                'agent_type': 'SQLEVALUATOR'
            }
        
        # Get default model config from workspace
        default_model_config = None
        if hasattr(state, 'workspace') and state.workspace and state.workspace.default_model:
            default_model_config = {
                'name': state.workspace.default_model.name,
                'ai_model': state.workspace.default_model
            }
        
        # Create SqlEvaluator agent
        sql_evaluator_agent = AgentInitializer.create_sql_evaluator_agent(
            test_evaluator_config, 
            default_model_config,
            retries=3
        )
        
        if not sql_evaluator_agent:
            error_msg = "Failed to create SqlEvaluator agent for Belt and Suspenders selection"
            logger.error(error_msg)
            return False, None, error_msg, _create_error_metrics(start_time, error_msg)
        
        # Prepare template data
        candidate_sqls_text = _format_candidate_sqls(generated_sqls)
        test_results_text = _format_test_results(evaluation_results)
        
        # Load user template
        user_template = TemplateLoader.load('template_sql_selector.txt')
        
        # Format template with data
        formatted_template = user_template.format(
            QUESTION=state.question or "User question not available",
            CANDIDATE_SQLs=candidate_sqls_text,
            TEST_RESULTS=test_results_text
        )
        
        logger.debug(f"Calling SqlEvaluator agent with {len(generated_sqls)} SQL candidates")
        
        # Call SqlEvaluator agent
        from model.evaluator_deps import EvaluatorDeps
        deps = EvaluatorDeps()
        
        result = await sql_evaluator_agent.run(formatted_template, deps=deps)
        
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Parse the result
        if result and hasattr(result, 'data') and hasattr(result.data, 'selected_sql_index'):
            selected_index = result.data.selected_sql_index
            justification = getattr(result.data, 'justification', 'SqlEvaluator selection')
            
            # Validate selected index
            if 0 <= selected_index < len(generated_sqls):
                selected_sql = generated_sqls[selected_index]
                
                # Create success metrics
                metrics = {
                    'total_sqls': len(generated_sqls),
                    'selection_method': 'belt_and_suspenders',
                    'selected_sql_index': selected_index,
                    'selection_reason': f"Belt and Suspenders: {justification}",
                    'processing_time_ms': duration_ms,
                    'agent_name': sql_evaluator_agent.name,
                    'evaluation_type': 'enhanced',
                    'final_status': 'BELT_AND_SUSPENDERS_SUCCESS'
                }
                
                logger.info(f"Belt and Suspenders selected SQL #{selected_index + 1}: {justification}")
                return True, selected_sql, None, metrics
            else:
                error_msg = f"SqlEvaluator returned invalid index {selected_index} for {len(generated_sqls)} SQLs"
                logger.error(error_msg)
                return False, None, error_msg, _create_error_metrics(start_time, error_msg)
        else:
            error_msg = "SqlEvaluator returned invalid or empty result"
            logger.error(error_msg)
            return False, None, error_msg, _create_error_metrics(start_time, error_msg)
            
    except Exception as e:
        error_msg = f"Belt and Suspenders selection failed: {str(e)}"
        log_error(f"Belt and Suspenders selection error: {error_msg}")
        return False, None, error_msg, _create_error_metrics(start_time, error_msg)


def _format_candidate_sqls(generated_sqls: List[str]) -> str:
    """Format SQL candidates for the template."""
    if not generated_sqls:
        return "No SQL candidates available"
    
    formatted_sqls = []
    for i, sql in enumerate(generated_sqls):
        formatted_sqls.append(f"**SQL #{i}:**\n```sql\n{sql.strip()}\n```")
    
    return "\n\n".join(formatted_sqls)


def _format_test_results(evaluation_results: List[Tuple[str, List[str]]]) -> str:
    """Format test results with failure details for the template."""
    if not evaluation_results or len(evaluation_results) == 0:
        return "No test results available"
    
    # Extract thinking and answers from first tuple
    thinking, answers = evaluation_results[0]
    
    if not answers:
        return "No test evaluation answers available"
    
    # Parse test results and collect failures
    formatted_results = []
    
    for answer_idx, answer in enumerate(answers):
        # Parse answer format: "SQL #1: OK, KO - missing WHERE clause, OK"
        if answer.startswith("SQL #"):
            # Extract SQL index and results
            parts = answer.split(":", 1)
            if len(parts) == 2:
                sql_header = parts[0].strip()
                results_str = parts[1].strip()
                
                # Split results by comma but handle "KO - reason" as a single unit
                test_results = []
                current_result = ""
                
                for part in results_str.split(","):
                    part = part.strip()
                    if part.upper() == "OK":
                        test_results.append("OK")
                    elif part.startswith("KO"):
                        if " - " in part:
                            # Complete KO with reason
                            test_results.append(part)
                        else:
                            # KO without complete reason, might continue in next part
                            current_result = part
                    elif current_result:
                        # This is continuation of a KO reason
                        current_result += ", " + part
                        test_results.append(current_result)
                        current_result = ""
                    else:
                        test_results.append(part)
                
                # Format the results for this SQL
                sql_result_lines = [sql_header]
                failed_tests = []
                
                for test_idx, test_result in enumerate(test_results):
                    if test_result.upper() != "OK":
                        failed_tests.append(f"  Test {test_idx + 1}: {test_result}")
                
                if failed_tests:
                    sql_result_lines.append("Failed Tests:")
                    sql_result_lines.extend(failed_tests)
                else:
                    sql_result_lines.append("All tests passed")
                
                formatted_results.append("\n".join(sql_result_lines))
    
    if formatted_results:
        return "\n\n".join(formatted_results)
    else:
        return "No detailed test failure information available"


def _create_error_metrics(start_time: datetime, error_message: str) -> Dict:
    """Create error metrics dictionary."""
    end_time = datetime.now()
    duration_ms = int((end_time - start_time).total_seconds() * 1000)
    
    return {
        'selection_method': 'belt_and_suspenders',
        'selection_reason': f"Belt and Suspenders failed: {error_message}",
        'processing_time_ms': duration_ms,
        'evaluation_type': 'enhanced',
        'final_status': 'BELT_AND_SUSPENDERS_FAILED',
        'error': error_message
    }