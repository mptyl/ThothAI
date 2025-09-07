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

# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""
SQL Selection module for choosing the best SQL from generated candidates
based on evaluation results and complexity analysis.
"""

import logging
import random
import re
from typing import List, Tuple, Dict, Optional, Any
from helpers.sql_complexity_analyzer import SQLComplexityAnalyzer
from .belt_and_suspenders_selection import perform_belt_and_suspenders_selection

logger = logging.getLogger(__name__)


class SQLSelectionError(Exception):
    """Custom exception for SQL selection errors"""
    pass


def parse_evaluation_answer(answer: str) -> Tuple[int, List[str]]:
    """
    Parse an evaluation answer in the new format.
    
    Args:
        answer: String like "SQL #1: OK, OK, KO - missing WHERE clause"
        
    Returns:
        Tuple of (sql_index, list_of_test_results)
        where test_results is ["OK", "KO - missing WHERE clause", ...]
    """
    # Extract SQL index from "SQL #n:" pattern (case-insensitive, flexible spacing)
    sql_match = re.match(r"(?i)SQL\s*#(\d+):\s*(.+)", answer.strip())
    if not sql_match:
        logger.warning(f"Could not parse answer format: '{answer}' (stripped: '{answer.strip()}')")
        # Log more details for debugging
        logger.debug(f"Answer length: {len(answer)}, starts with: {answer[:20] if len(answer) > 20 else answer}")
        return -1, []
    
    sql_index = int(sql_match.group(1)) - 1  # Convert to 0-based index
    results_str = sql_match.group(2)
    
    # Split by comma but handle "KO - reason" as a single unit
    test_results = []
    current_result = ""
    
    for part in results_str.split(","):
        part = part.strip()
        if part.startswith("OK") or (part.startswith("KO") and " - " in part):
            # Complete test result
            test_results.append(part)
        elif current_result:
            # This is part of a KO reason that contained a comma
            current_result += ", " + part
            if current_result.startswith("KO"):
                test_results.append(current_result)
                current_result = ""
        elif part.startswith("KO"):
            # Start of a KO that might have a reason with commas
            current_result = part
        else:
            # Standalone result
            test_results.append(part)
    
    # Add any remaining partial result
    if current_result:
        test_results.append(current_result)
    
    return sql_index, test_results


def calculate_detailed_sql_scores(
    generated_sqls: List[str],
    evaluation_results: List[Tuple[str, List[str]]]
) -> List[Dict]:
    """
    Calculate pass rates for each SQL based on detailed evaluation results.
    
    Args:
        generated_sqls: List of generated SQL queries
        evaluation_results: List of tuples [(thinking, answers)]
            where answers is list of "SQL #n: OK, KO - reason, ..." strings
        
    Returns:
        List of dictionaries with SQL scores and detailed test results
    """
    # Handle new format: List[Tuple[str, List[str]]]
    if not evaluation_results or len(evaluation_results) == 0:
        return []
    
    # Extract thinking and answers from first tuple
    thinking, answers = evaluation_results[0]
    test_units = []  # No longer available in new format
    sql_scores = []
    
    # Initialize scores for all SQLs
    for sql_idx in range(len(generated_sqls)):
        sql_scores.append({
            "sql_index": sql_idx,
            "passed_count": 0,
            "total_tests": 0,
            "pass_rate": 0.0,
            "test_details": [],  # List of (test, result) tuples
            "failure_reasons": []  # List of failure reasons
        })
    
    # Parse each answer to extract detailed test results
    logger.debug(f"Processing {len(answers)} evaluation answers")
    for answer_idx, answer in enumerate(answers):
        logger.debug(f"Processing answer {answer_idx + 1}: {answer[:100]}..." if len(answer) > 100 else f"Processing answer {answer_idx + 1}: {answer}")
        sql_idx, test_results = parse_evaluation_answer(answer)
        
        if sql_idx < 0 or sql_idx >= len(generated_sqls):
            logger.warning(f"Invalid SQL index {sql_idx} in answer: {answer}")
            continue
        
        logger.debug(f"SQL {sql_idx + 1} has {len(test_results)} test results")
        
        # Process test results for this SQL
        for test_idx, test_result in enumerate(test_results):
            # Always use Test number format since test_units is empty in new format
            test_name = f"Test {test_idx + 1}"
            
            sql_scores[sql_idx]["total_tests"] += 1
            
            if test_result.strip().upper() == "OK":
                sql_scores[sql_idx]["passed_count"] += 1
                sql_scores[sql_idx]["test_details"].append((test_name, "OK"))
            else:
                # Extract failure reason from "KO - reason" or provide meaningful default
                if " - " in test_result:
                    _, reason = test_result.split(" - ", 1)
                    # Keep the full test description but format it nicely
                    # Add a line break between test and reason for readability
                    sql_scores[sql_idx]["failure_reasons"].append({
                        "test_num": test_idx + 1,
                        "test_desc": test_name,
                        "reason": reason
                    })
                else:
                    # Provide a more meaningful default reason based on the test result
                    if test_result.strip().upper() in ["ERROR", "KO", "FAIL", "FAILED"]:
                        default_reason = "SQL does not conform to test requirements - validation failed without specific details"
                    elif test_result.strip().upper() == "TIMEOUT":
                        default_reason = "Test execution timed out - SQL may be too complex or contain infinite loops"
                    elif test_result.strip().upper() == "SYNTAX_ERROR":
                        default_reason = "SQL syntax error detected during test execution"
                    elif test_result.strip():
                        # If there's some text but no dash separator, use it as the reason
                        default_reason = f"Test validation failed: {test_result.strip()}"
                    else:
                        # Empty or whitespace-only result
                        default_reason = "SQL does not conform to test requirements - no evaluation details available"
                    
                    sql_scores[sql_idx]["failure_reasons"].append({
                        "test_num": test_idx + 1,
                        "test_desc": test_name,
                        "reason": default_reason
                    })
                sql_scores[sql_idx]["test_details"].append((test_name, test_result))
    
    # Calculate pass rates
    for score in sql_scores:
        if score["total_tests"] > 0:
            score["pass_rate"] = score["passed_count"] / score["total_tests"]
        
        logger.info(f"SQL #{score['sql_index'] + 1}: {score['passed_count']}/{score['total_tests']} "
                   f"tests passed ({score['pass_rate']:.1%})")
        if score["failure_reasons"]:
            for failure in score["failure_reasons"]:
                if isinstance(failure, dict):
                    logger.debug(f"  - Test {failure['test_num']}: {failure['reason']}")
                else:
                    # Backward compatibility
                    logger.debug(f"  - {failure}")
    
    return sql_scores


# NOTE: Removed small_bug_fixer function
# This function was automatically adding NULLS LAST/FIRST clauses that could cause issues with older SQLite versions
# SQLite 3.30.0+ (October 2019) supports NULLS LAST/FIRST, so modern systems handle this correctly
# NULLS LAST/FIRST handling is now done in SQL generation templates and works for all modern databases


# NOTE: Removed fix_nulls_ordering function  
# SQLite 3.30.0+ supports NULLS LAST/FIRST, so this workaround is no longer needed
# The templates now generate proper NULLS clauses for all databases including modern SQLite


async def select_best_sql(
    generated_sqls: List[str],
    evaluation_results,  # List[Tuple[str, List[str]]] (new format)
    evaluation_threshold: int = 90,  # Now an integer percentage from workspace
    state: Optional[Any] = None,  # SystemState for Belt and Suspenders
    agents_and_tools: Optional[Any] = None  # Agent manager for Belt and Suspenders
) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """
    Select the best SQL from generated candidates based on evaluation results.
    
    Args:
        generated_sqls: List of generated SQL queries
        evaluation_results: Tuple (thinking, answers, test_units) with detailed evaluations
        evaluation_threshold: Minimum percentage of tests to pass (from workspace, 0-100)
        state: SystemState for Belt and Suspenders functionality (optional)
        agents_and_tools: Agent manager for Belt and Suspenders functionality (optional)
        
    Returns:
        Tuple of (success, selected_sql, error_message, metrics)
        - success: True if a SQL was selected
        - selected_sql: The selected SQL query or None
        - error_message: Error message if selection failed (formatted message if no SQL passes threshold)
        - metrics: Dictionary with selection metrics including detailed test results
    """
    # Convert integer percentage to float ratio
    min_pass_threshold = evaluation_threshold / 100.0
    
    metrics = {
        "total_sqls": len(generated_sqls),
        "evaluation_threshold": evaluation_threshold,
        "sql_scores": [],
        "finalists": [],
        "selection_reason": ""
    }
    
    # Edge case: No SQL generated
    if not generated_sqls:
        error_msg = "No SQL queries were generated. Cannot proceed with selection."
        logger.error(error_msg)
        return False, None, error_msg, metrics
    
    # Edge case: No evaluation results
    if not evaluation_results:
        error_msg = "No test evaluations were generated. Cannot validate SQL queries."
        logger.error(error_msg)
        return False, None, error_msg, metrics
    
    # Parse the new format: List[Tuple[str, List[str]]]
    if isinstance(evaluation_results, list) and len(evaluation_results) > 0:
        # Extract thinking and answers from first tuple (we expect only one)
        thinking, answers = evaluation_results[0]
        # We no longer have test_units in the new format
        test_units = []  # Empty list as placeholder
        
        # Check if we have valid evaluation data
        if not answers:
            error_msg = "No evaluation answers were provided. Cannot assess SQL quality."
            logger.error(error_msg)
            return False, None, error_msg, metrics
        
        # Calculate detailed scores with the new format
        sql_scores = calculate_detailed_sql_scores(generated_sqls, evaluation_results)
        
        # IMPORTANT: Always include detailed scores in metrics for logging
        metrics["sql_scores"] = sql_scores
        
        # Check for Belt and Suspenders enhanced selection
        belt_and_suspenders_enabled = False
        if state and hasattr(state, 'workspace') and state.workspace:
            belt_and_suspenders_enabled = state.workspace.get('belt_and_suspenders', False)
        
        if belt_and_suspenders_enabled and agents_and_tools:
            # Check if this is a borderline case (B or C)
            if is_borderline_case(sql_scores, min_pass_threshold):
                logger.info("Belt and Suspenders enabled for borderline evaluation case")
                
                # Attempt Belt and Suspenders selection
                try:
                    from datetime import datetime
                    
                    # Record timing
                    if hasattr(state, 'execution'):
                        state.execution.belt_and_suspenders_start_time = datetime.now()
                    
                    # Perform Belt and Suspenders selection
                    success, selected_sql, error_message, bs_metrics = await perform_belt_and_suspenders_selection(
                        state, generated_sqls, evaluation_results, agents_and_tools
                    )
                    
                    # Record end timing
                    if hasattr(state, 'execution') and state.execution.belt_and_suspenders_start_time:
                        end_time = datetime.now()
                        state.execution.belt_and_suspenders_end_time = end_time
                        duration_ms = (end_time - state.execution.belt_and_suspenders_start_time).total_seconds() * 1000
                        state.execution.belt_and_suspenders_duration_ms = duration_ms
                    
                    if success and selected_sql:
                        # Update metrics with Belt and Suspenders results
                        metrics.update(bs_metrics)
                        metrics["selection_reason"] = bs_metrics.get("selection_reason", "Belt and Suspenders selection")
                        logger.info("Belt and Suspenders selection completed successfully")
                        return True, selected_sql, None, metrics
                    else:
                        logger.warning(f"Belt and Suspenders selection failed: {error_message}")
                        # Continue with regular selection as fallback
                        
                except Exception as e:
                    logger.error(f"Belt and Suspenders selection error: {str(e)}")
                    # Continue with regular selection as fallback
                    
        else:
            if belt_and_suspenders_enabled:
                logger.debug("Belt and Suspenders enabled but agents_and_tools not available")
            else:
                logger.debug("Belt and Suspenders not enabled for this workspace")
        # test_units is not available in the new format
        if test_units:
            metrics["test_units"] = test_units  # Include test descriptions if available
        
        # Find SQLs above threshold and determine the best pass rate among them
        candidates_above_threshold = [s for s in sql_scores if s["pass_rate"] >= min_pass_threshold]
        
        if not candidates_above_threshold:
            # No SQL meets the threshold - return formatted error message
            # This will be handled below at line 336
            pass
        else:
            # Sort by pass rate descending to find the best rate
            candidates_above_threshold.sort(key=lambda x: x["pass_rate"], reverse=True)
            best_rate = candidates_above_threshold[0]["pass_rate"]
            
            # Find all SQLs with the best pass rate (these are the true "finalists")
            finalists = [s for s in candidates_above_threshold if s["pass_rate"] == best_rate]
            metrics["finalists"] = finalists
            
            if len(finalists) == 1:
                # Single finalist - select it directly
                selected_idx = finalists[0]["sql_index"]
                selected_sql = generated_sqls[selected_idx]
                pass_rate = finalists[0]["pass_rate"]
                if pass_rate == 1.0:
                    metrics["selection_reason"] = "Single SQL with 100% pass rate"
                    logger.info(f"Selected SQL #{selected_idx + 1} - only SQL with 100% pass rate")
                else:
                    metrics["selection_reason"] = f"Single best SQL with {pass_rate:.1%} pass rate"
                    logger.info(f"Selected SQL #{selected_idx + 1} with highest pass rate {pass_rate:.1%}")
                return True, selected_sql, None, metrics
            else:
                # Multiple finalists with same best pass rate - select the simplest
                selected_sql = select_simplest_sql(
                    generated_sqls, 
                    [f["sql_index"] for f in finalists]
                )
                if selected_sql:
                    pass_rate = finalists[0]["pass_rate"]
                    if pass_rate == 1.0:
                        metrics["selection_reason"] = "Simplest among multiple 100% pass finalists"
                        logger.info(f"Selected simplest SQL from {len(finalists)} SQLs with 100% pass rate")
                    else:
                        metrics["selection_reason"] = f"Simplest among {len(finalists)} SQLs with {pass_rate:.1%} pass rate"
                        logger.info(f"Selected simplest SQL from {len(finalists)} SQLs with best pass rate {pass_rate:.1%}")
                    return True, selected_sql, None, metrics
                else:
                    # Fallback: if select_simplest_sql fails, select the first finalist
                    selected_idx = finalists[0]["sql_index"]
                    selected_sql = generated_sqls[selected_idx]
                    pass_rate = finalists[0]["pass_rate"]
                    if pass_rate == 1.0:
                        metrics["selection_reason"] = "First among multiple 100% pass finalists (complexity analysis failed)"
                        logger.warning(f"Complexity analysis failed, selected first SQL #{selected_idx + 1} with 100% pass rate")
                    else:
                        metrics["selection_reason"] = f"First SQL with {pass_rate:.1%} pass rate (complexity analysis failed)"
                        logger.warning(f"Complexity analysis failed, selected first SQL #{selected_idx + 1} with {pass_rate:.1%} pass rate")
                    return True, selected_sql, None, metrics
        
        # If we reach here, no SQL meets the threshold - return formatted error message
        # Log detailed test results for Django
        logger.warning(f"No SQL met the {evaluation_threshold}% threshold")
        
        # Log complete evaluation details for each SQL
        logger.info("=== DETAILED EVALUATION RESULTS ===")
        for score in sql_scores:
            sql_idx = score['sql_index']
            logger.info(f"SQL #{sql_idx + 1}: {score['passed_count']}/{score['total_tests']} tests passed ({score['pass_rate']:.1%})")
            
            # Log the actual SQL if available
            if generated_sqls and sql_idx < len(generated_sqls):
                logger.info(f"SQL #{sql_idx + 1} Query:")
                logger.info(generated_sqls[sql_idx])
            
            # Log all failed tests with details
            if score['failure_reasons']:
                logger.info(f"Failed tests for SQL #{sql_idx + 1}:")
                for failure in score['failure_reasons']:
                    if isinstance(failure, dict):
                        logger.info(f"  Test {failure['test_num']}: {failure['test_desc']}")
                        logger.info(f"    Reason: {failure['reason']}")
                    else:
                        logger.info(f"  {failure}")
        
        # Log all test units that were evaluated
        if test_units:
            logger.info("=== ALL TEST CRITERIA EVALUATED ===")
            for idx, test_unit in enumerate(test_units, 1):
                logger.info(f"Test {idx}: {test_unit}")
        
        logger.info("=== END DETAILED EVALUATION ===")
        
        # Format user-friendly message (without test details)
        error_msg = format_failure_message(sql_scores, evaluation_threshold, test_units, 
                                          generated_sqls=generated_sqls)
        # IMPORTANT: Still include all metrics for logging purposes
        metrics["selection_reason"] = f"No SQL met the {evaluation_threshold}% threshold"
        return False, None, error_msg, metrics
    else:
        # Invalid format
        error_msg = "Invalid evaluation results format"
        logger.error(error_msg)
        return False, None, error_msg, metrics
    
    # This should never be reached
    error_msg = "Unexpected error in SQL selection logic"
    logger.error(error_msg)
    return False, None, error_msg, metrics


def format_failure_message(sql_scores: List[Dict], threshold: int, test_units: List[str], 
                          generated_sqls: List[str] = None) -> str:
    """
    Format a user-friendly message when no SQL passes the threshold.
    Shows detailed test failures for transparency.
    
    Args:
        sql_scores: List of SQL score dictionaries with test details
        threshold: The threshold percentage that was not met
        test_units: List of test descriptions
        generated_sqls: List of generated SQL queries (optional, for showing the actual SQL)
        
    Returns:
        Formatted error message for the user with detailed test results
    """
    message = "## SQL Generation Quality Check Failed\n\n"
    message += f"Unfortunately, none of the generated SQL queries passed the required quality threshold of **{threshold}%**.\n\n"
    
    # Find the best performing SQL for feedback
    if sql_scores:
        best_sql = max(sql_scores, key=lambda x: x["pass_rate"])
        
        message += f"### Best Result (SQL #{best_sql['sql_index'] + 1}):\n"
        message += f"**Tests passed**: {best_sql['pass_rate']:.0%} ({best_sql['passed_count']}/{best_sql['total_tests']} tests)\n\n"
        
        # Show the actual SQL query if available
        if generated_sqls and best_sql['sql_index'] < len(generated_sqls):
            message += "#### Generated SQL:\n"
            message += "```sql\n"
            message += generated_sqls[best_sql['sql_index']]
            message += "\n```\n\n"
        
        # Show failed tests with their reasons
        if best_sql["failure_reasons"]:
            message += "### Failed Tests:\n\n"
            for failure in best_sql["failure_reasons"]:
                if isinstance(failure, dict):
                    # Show test number with description
                    message += f"**Test {failure['test_num']}:** {failure['test_desc']}\n"
                    # Show why it failed (the KO reason) - indented for clarity
                    message += f"   **→ Failed:** {failure['reason']}\n\n"
                else:
                    # Backward compatibility for string format
                    message += f"- {failure}\n"
            message += "\n"
        
        # Show all test criteria that were evaluated
        if test_units and len(test_units) > 0:
            message += "### All Test Criteria:\n"
            message += "<details>\n"
            message += "<summary>Click to expand all test criteria</summary>\n\n"
            for idx, test_unit in enumerate(test_units, 1):
                # Truncate very long test descriptions for readability
                if len(test_unit) > 200:
                    display_test = test_unit[:197] + "..."
                else:
                    display_test = test_unit
                message += f"{idx}. {display_test}\n"
            message += "\n</details>\n\n"
    
    # What This Means section
    message += "### What This Means:\n"
    message += "The generated SQL queries did not meet the quality criteria required for reliable results. "
    message += "This could be due to:\n"
    message += "- Complex question requirements\n"
    message += "- Ambiguous phrasing\n"
    message += "- Database schema limitations\n\n"
    
    message += "### Suggestions:\n"
    message += "- Try rephrasing your question more specifically\n"
    message += "- Break down complex queries into simpler parts\n"
    message += "- Ensure the question aligns with available data\n"
    
    return message


def find_finalists(sql_scores: List[Dict], threshold: float) -> List[Dict]:
    """
    Find SQL queries that meet or exceed the threshold pass rate.
    
    Args:
        sql_scores: List of SQL score dictionaries
        threshold: Minimum pass rate threshold (0.0 to 1.0)
        
    Returns:
        List of finalist SQL score dictionaries
    """
    finalists = [
        score for score in sql_scores 
        if score["pass_rate"] >= threshold
    ]
    
    logger.info(f"Found {len(finalists)} SQLs with pass rate >= {threshold:.0%}")
    return finalists


def is_borderline_case(sql_scores: List[Dict], min_pass_threshold: float) -> bool:
    """
    Determine if evaluation results represent a borderline case (B or C).
    
    Case B: Multiple SQLs with 100% pass rate (need to choose among perfect options)
    Case C: Some SQLs above threshold but not perfect (need enhanced evaluation)
    
    Args:
        sql_scores: List of SQL score dictionaries with pass rates
        min_pass_threshold: Minimum pass rate threshold (0.0 to 1.0)
        
    Returns:
        True if this is a borderline case B or C
    """
    # Find SQLs above threshold
    candidates_above_threshold = [s for s in sql_scores if s["pass_rate"] >= min_pass_threshold]
    
    if not candidates_above_threshold:
        return False  # Case D (all failed) - not borderline
    
    # Find perfect SQLs (100% pass rate)
    perfect_sqls = [s for s in candidates_above_threshold if s["pass_rate"] >= 1.0]
    
    # Case B: Multiple perfect SQLs
    if len(perfect_sqls) > 1:
        return True
    
    # Case C: Some above threshold but not perfect
    if len(perfect_sqls) == 0 and len(candidates_above_threshold) > 0:
        return True
    
    # Case A: Single perfect SQL - not borderline
    return False


def select_simplest_sql(
    generated_sqls: List[str],
    candidate_indices: List[int]
) -> Optional[str]:
    """
    Select the simplest SQL from a list of candidates using complexity analysis.
    
    Args:
        generated_sqls: List of all generated SQL queries
        candidate_indices: Indices of candidate SQLs to compare
        
    Returns:
        The simplest SQL query or None if error
    """
    if not candidate_indices:
        return None
    
    if len(candidate_indices) == 1:
        return generated_sqls[candidate_indices[0]]
    
    try:
        analyzer = SQLComplexityAnalyzer()
        
        # Calculate complexity scores for all candidates
        complexity_scores = []
        for idx in candidate_indices:
            sql = generated_sqls[idx]
            metrics = analyzer.analyze_query(sql)
            score = analyzer.calculate_complexity_score(metrics)
            complexity_scores.append((idx, score))
            logger.debug(f"SQL #{idx + 1} complexity score: {score}")
        
        # Sort by complexity (ascending - lowest is simplest)
        complexity_scores.sort(key=lambda x: x[1])
        
        # Check for ties
        min_score = complexity_scores[0][1]
        tied_indices = [idx for idx, score in complexity_scores if score == min_score]
        
        if len(tied_indices) > 1:
            # Random selection among tied SQLs
            selected_idx = random.choice(tied_indices)
            logger.info(f"Multiple SQLs tied for simplest (score: {min_score}). Randomly selected SQL #{selected_idx + 1}")
        else:
            selected_idx = complexity_scores[0][0]
            logger.info(f"SQL #{selected_idx + 1} is the simplest (score: {min_score})")
        
        return generated_sqls[selected_idx]
        
    except Exception as e:
        # Error in complexity analyzer - fall back to random selection
        logger.error(f"Error in SQL complexity analysis: {e}. Falling back to random selection.")
        selected_idx = random.choice(candidate_indices)
        logger.info(f"Randomly selected SQL #{selected_idx + 1} due to complexity analyzer error")
        return generated_sqls[selected_idx]