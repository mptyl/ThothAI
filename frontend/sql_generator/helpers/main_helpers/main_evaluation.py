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
Autonomous evaluation system for SQL candidates.
Runs evaluators in parallel with fixed temperature to achieve 100% evaluation reliability.
"""

import logging
import asyncio
from typing import List, Tuple, Any, Optional, Dict
from pydantic_ai.settings import ModelSettings
from model.evaluator_deps import EvaluatorDeps
from helpers.template_preparation import TemplateLoader
from agents.test_reducer_agent import run_test_reducer
from agents.core.agent_initializer import AgentInitializer

logger = logging.getLogger(__name__)

# Fixed temperature for all evaluators
EVALUATOR_TEMPERATURE = 0.2


async def evaluate_single_sql(
    evaluator_agent,
    sql_query: str, 
    sql_index: int,
    filtered_test_answers: List[str],
    context: Dict[str, Any]
) -> Tuple[int, str, List[str]]:
    """
    Evaluate a single SQL query against all tests.
    
    Args:
        evaluator_agent: The evaluator agent to use
        sql_query: The SQL query to evaluate
        sql_index: The index of this SQL (for tracking)
        filtered_test_answers: List of test units to apply
        context: Context dictionary with question, schema, etc.
        
    Returns:
        Tuple of (sql_index, thinking, test_results)
        where test_results is a list of "Test #N: OK" or "Test #N: KO - reason"
    """
    try:
        # Format tests as numbered list
        unit_tests_str = "\n".join([f"{i}. {test}" for i, test in enumerate(filtered_test_answers, 1)])
        
        # Create evaluation template for single SQL
        template = TemplateLoader.format(
            'template_evaluate_single.txt',
            safe=True,
            QUESTION=context['question'],
            DATABASE_TYPE=context['database_type'],
            DATABASE_SCHEMA=context['database_schema'],
            DIRECTIVES=context['directives'],
            EVIDENCE=context['evidence'],
            SQL_QUERY=sql_query,
            UNIT_TESTS=unit_tests_str,
            GOLD_SQL_EXAMPLES=context['gold_sql_examples']
        )
        
        # Run evaluator with fixed temperature
        result = await evaluator_agent.run(
            template,
            model_settings=ModelSettings(temperature=EVALUATOR_TEMPERATURE),
            deps=EvaluatorDeps()
        )
        
        if result and hasattr(result, 'output'):
            thinking = getattr(result.output, 'thinking', '')
            answers = getattr(result.output, 'answers', [])
            
            # Validate we got the right number of test results
            if len(answers) != len(filtered_test_answers):
                logger.warning(f"SQL #{sql_index+1}: Expected {len(filtered_test_answers)} test results, got {len(answers)}")
                # Pad or truncate as needed
                if len(answers) < len(filtered_test_answers):
                    for i in range(len(answers) + 1, len(filtered_test_answers) + 1):
                        answers.append(f"Test #{i}: KO - incomplete evaluation")
                else:
                    answers = answers[:len(filtered_test_answers)]
            
            return (sql_index, thinking, answers)
        else:
            logger.error(f"Evaluator returned no output for SQL #{sql_index+1}")
            error_answers = [f"Test #{i}: KO - evaluation failed" for i in range(1, len(filtered_test_answers) + 1)]
            return (sql_index, "Evaluation failed - no output", error_answers)
            
    except Exception as e:
        logger.error(f"Evaluation failed for SQL #{sql_index+1}: {e}")
        error_answers = [f"Test #{i}: KO - evaluation error" for i in range(1, len(filtered_test_answers) + 1)]
        return (sql_index, f"Evaluation error: {str(e)}", error_answers)


async def evaluate_sql_candidates(state, agents_and_tools):
    """
    Evaluate SQL candidates against generated tests.
    Extracts all unique test answers and runs a SINGLE evaluator agent with the complete deduplicated list.
    
    Args:
        state: System state containing generated tests and SQL candidates
        agents_and_tools: Agent manager with evaluator agent
        
    Returns:
        Single tuple (thinking, answers, test_units) with evaluation results
        - thinking: The evaluator's reasoning
        - answers: List of verdicts for each SQL candidate
        - test_units: List of deduplicated test units that were applied
    """
    # Get the evaluator agent from agents_and_tools
    evaluator_agent = getattr(agents_and_tools, 'evaluator_agent', None)
    
    if not evaluator_agent:
        logger.error("No evaluator_agent found in workspace configuration")
        return ("No evaluator agent available", [], [])
    
    # Check if we have tests to evaluate
    if not hasattr(state, 'generated_tests') or not state.generated_tests:
        logger.warning("No generated tests found for evaluation")
        return ("No tests available for evaluation", [], [])
    
    # Check if we have SQL candidates to evaluate
    if not hasattr(state, 'generated_sqls') or not state.generated_sqls:
        logger.warning("No SQL candidates found for evaluation")
        return ("No SQL candidates to evaluate", [], [])
    
    # Extract all test answers from all generated tests
    all_test_answers = []
    combined_thinking = []
    
    for i, (thinking, answers) in enumerate(state.generated_tests, 1):
        # Collect all answers
        all_test_answers.extend(answers)
        # Collect thinking for context (optional, for combined context)
        if thinking and thinking != "GENERATION FAILED":
            combined_thinking.append(f"Test Set {i} thinking: {thinking}")
    
    # Deduplicate test answers while preserving order
    seen = set()
    unique_test_answers = []
    for answer in all_test_answers:
        if answer not in seen and answer != "GENERATION FAILED":
            seen.add(answer)
            unique_test_answers.append(answer)
    
    if not unique_test_answers:
        logger.error("No valid test answers after deduplication")
        return ("No valid tests available after deduplication", ["Failed - no tests"] * len(state.generated_sqls), [])
    
    logger.info(f"Deduplicated {len(all_test_answers)} test answers to {len(unique_test_answers)} unique tests")
    
    # Apply semantic filtering using TestReducer if available and beneficial
    filtered_test_answers = unique_test_answers
    # Only enable semantic filtering when multiple test generators are active
    multiple_test_generators_active = False
    try:
        pools = getattr(agents_and_tools, 'agent_pools', None)
        if pools:
            test_pool = getattr(pools, 'test_unit_generation_agents_pool', []) or []
            # Count non-None agents
            multiple_test_generators_active = len([a for a in test_pool if a is not None]) > 1
    except Exception as e:
        logger.debug(f"Could not determine test generator pool size: {e}")
    
    if multiple_test_generators_active and len(unique_test_answers) > 5:  # Use TestReducer only if beneficial and multiple generators
        try:
            # Extract model config from evaluator agent or workspace
            evaluator_model_config = None
            
            # First try to get from state if available
            if hasattr(state, 'workspace_config') and state.workspace_config:
                evaluator_model_config = state.workspace_config.get('test_evaluator_agent')
                if not evaluator_model_config:
                    # Fallback to test_gen_agent_1 for backward compatibility
                    evaluator_model_config = state.workspace_config.get('test_gen_agent_1')
            
            # Then try to extract from the agent itself
            if not evaluator_model_config and evaluator_agent:
                if hasattr(evaluator_agent, 'agent_config'):
                    evaluator_model_config = evaluator_agent.agent_config
                elif hasattr(evaluator_agent, 'model_config'):
                    evaluator_model_config = evaluator_agent.model_config
                
            # If still no config, skip TestReducer
            if not evaluator_model_config:
                logger.debug("No evaluator model config available for TestReducer, skipping semantic filtering")
                test_reducer_agent = None
            else:
                # Create TestReducer agent with evaluator's config
                test_reducer_agent = AgentInitializer.create_test_reducer_agent(
                    agent_config=evaluator_model_config,
                    default_model_config=None,
                    retries=1
                )
            
            if test_reducer_agent:
                logger.info(f"Applying semantic filtering to {len(unique_test_answers)} tests using TestReducer")
                
                # Prepare thinking context from test generation
                test_thinking = combined_thinking[0] if combined_thinking else "Test generation thinking"
                database_schema = state.used_mschema if hasattr(state, 'used_mschema') else state.full_mschema if hasattr(state, 'full_mschema') else ""
                
                # Run TestReducer
                reducer_result = await run_test_reducer(
                    test_reducer_agent,
                    unique_test_answers,
                    test_thinking,
                    state.question,
                    database_schema
                )
                
                if reducer_result and reducer_result.reduced_tests:
                    filtered_test_answers = reducer_result.reduced_tests
                    logger.info(f"TestReducer successfully reduced tests from {len(unique_test_answers)} to {len(filtered_test_answers)}")
                    
                    # Save filtered tests in state if possible
                    if hasattr(state, 'filtered_tests'):
                        state.filtered_tests = filtered_test_answers
                else:
                    logger.warning("TestReducer returned no results, using deduplicated tests")
            else:
                logger.debug("TestReducer agent could not be created, using deduplicated tests")
        except Exception as e:
            logger.error(f"Error during semantic test filtering: {e}, using deduplicated tests")
    else:
        # Log why semantic filtering was skipped
        if not multiple_test_generators_active:
            logger.info("Skipping semantic test filtering: only one test generator active")
        elif len(unique_test_answers) <= 5:
            logger.debug("Skipping semantic test filtering: not enough tests to benefit")
     
    # Combine test thinking for context (using first non-failed thinking or combined summary)
    test_thinking = "\n\n".join(combined_thinking) if combined_thinking else "Test generation thinking not available"
    
    # Format Gold SQL examples if available
    gold_sql_examples_str = ""
    if hasattr(state, 'gold_sql_examples') and state.gold_sql_examples:
        formatted_gold_examples = []
        for i, gold_sql in enumerate(state.gold_sql_examples, 1):
            formatted_gold_examples.append(f"Example #{i}:\n{gold_sql}")
        gold_sql_examples_str = "\n\n".join(formatted_gold_examples)
    else:
        gold_sql_examples_str = "No Gold SQL examples available for reference."
    
    # Prepare context for evaluations
    context = {
        'question': state.question,
        'database_type': state.dbmanager.db_type if state.dbmanager else 'sqlite',
        'database_schema': state.used_mschema if hasattr(state, 'used_mschema') else state.full_mschema,
        'directives': state.directives if hasattr(state, 'directives') else '',
        'evidence': state.evidence_for_template if hasattr(state, 'evidence_for_template') else '',
        'test_thinking': test_thinking,
        'gold_sql_examples': gold_sql_examples_str
    }
    
    # Store filtered tests for later use
    if hasattr(state, 'test_answers'):
        state.test_answers = filtered_test_answers
    if hasattr(state, 'filtered_tests'):
        state.filtered_tests = filtered_test_answers
    
    # Evaluate each SQL in parallel if multiple, otherwise single evaluation
    sql_count = len(state.generated_sqls)
    logger.info(f"Evaluating {sql_count} SQL candidates against {len(filtered_test_answers)} tests")
    
    if sql_count == 1:
        # Single SQL - evaluate directly
        sql_index, thinking, test_results = await evaluate_single_sql(
            evaluator_agent,
            state.generated_sqls[0],
            0,
            filtered_test_answers,
            context
        )
        
        # Convert test results to SQL verdict format
        sql_verdict = aggregate_test_results_to_sql_verdict(1, test_results)
        return [(thinking, [sql_verdict])]
    else:
        # Multiple SQLs - evaluate in parallel
        evaluation_tasks = [
            evaluate_single_sql(
                evaluator_agent,
                sql,
                i,
                filtered_test_answers,
                context
            )
            for i, sql in enumerate(state.generated_sqls)
        ]
        
        # Run all evaluations in parallel
        results = await asyncio.gather(*evaluation_tasks, return_exceptions=True)
        
        # Process results and aggregate
        sql_verdicts = []
        combined_thinking = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Evaluation task failed: {result}")
                sql_verdicts.append(f"SQL #{len(sql_verdicts)+1}: Failed - evaluation error")
                combined_thinking.append(f"SQL #{len(sql_verdicts)}: Evaluation failed")
            else:
                sql_index, thinking, test_results = result
                # Convert test results to SQL verdict format  
                sql_verdict = aggregate_test_results_to_sql_verdict(sql_index + 1, test_results)
                sql_verdicts.append(sql_verdict)
                if thinking:
                    combined_thinking.append(f"SQL #{sql_index+1}: {thinking}")
        
        # Return aggregated results
        final_thinking = "\n".join(combined_thinking) if combined_thinking else "Parallel evaluation complete"
        return [(final_thinking, sql_verdicts)]


def aggregate_test_results_to_sql_verdict(sql_number: int, test_results: List[str]) -> str:
    """
    Aggregate test results into SQL verdict format.
    
    Args:
        sql_number: The SQL number (1-based)
        test_results: List of "Test #N: OK" or "Test #N: KO - reason"
        
    Returns:
        String in format "SQL #N: OK, KO - reason, OK, ..."
    """
    # Extract just the OK/KO parts from test results
    verdicts = []
    for test_result in test_results:
        if ": " in test_result:
            # Extract the part after ": "
            verdict = test_result.split(": ", 1)[1]
            verdicts.append(verdict)
        else:
            # Fallback if format is unexpected
            verdicts.append("KO - unknown format")
    
    return f"SQL #{sql_number}: {', '.join(verdicts)}"


def determine_evaluation_case(evaluation_answers: List[str], threshold: float = 0.9) -> Tuple[str, Dict[str, Any]]:
    """
    Determine evaluation case (A/B/C/D) from evaluation answers.
    
    Args:
        evaluation_answers: List of SQL verdicts like "SQL #1: OK, OK, KO - reason"
        threshold: Pass rate threshold (default 0.9 for 90%)
        
    Returns:
        Tuple of (case, details) where:
        - case: "A", "B", "C", or "D"
        - details: Dictionary with pass_rates, perfect_sqls, etc.
    """
    pass_rates = {}
    
    for answer in evaluation_answers:
        if not answer.startswith("SQL #"):
            continue
            
        # Parse SQL identifier and test results
        parts = answer.split(":", 1)
        if len(parts) != 2:
            continue
            
        sql_id = parts[0].strip()
        test_results = parts[1].strip()
        
        # Count OK vs total tests
        results_list = [r.strip() for r in test_results.split(",")]
        ok_count = sum(1 for result in results_list if result == "OK")
        total_count = len(results_list)
        
        if total_count > 0:
            pass_rate = ok_count / total_count
            pass_rates[sql_id] = pass_rate
    
    # Classify SQLs
    perfect_sqls = [sql_id for sql_id, rate in pass_rates.items() if rate >= 1.0]
    above_threshold = [sql_id for sql_id, rate in pass_rates.items() if rate >= threshold]
    below_threshold = [sql_id for sql_id, rate in pass_rates.items() if rate < threshold]
    
    # Determine case
    if len(perfect_sqls) == 1 and len(pass_rates) == 1:
        case = "A"  # Single perfect SQL
    elif len(perfect_sqls) > 1:
        case = "B"  # Multiple perfect SQLs
    elif len(above_threshold) > 0:
        case = "C"  # Some SQLs above threshold but not perfect
    else:
        case = "D"  # All failed
        
    details = {
        'pass_rates': pass_rates,
        'perfect_sqls': perfect_sqls,
        'above_threshold': above_threshold,
        'below_threshold': below_threshold
    }
    
    return case, details


def process_evaluation_results(results: List[Any], num_sql_candidates: int) -> List[Tuple[str, List[str]]]:
    """
    Process evaluation results with failure explanations.
    
    Args:
        results: Raw results from parallel evaluation
        num_sql_candidates: Number of SQL candidates being evaluated
        
    Returns:
        List of tuples (thinking, answers) with proper failure handling
    """
    processed = []
    
    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            # Fallback for failed evaluations
            logger.error(f"Evaluation {i} failed with exception: {result}")
            error_answers = [f"Failed - evaluation error: {str(result)[:50]}"] * num_sql_candidates
            processed.append((f"Evaluation failed: {str(result)}", error_answers))
        else:
            try:
                # Extract thinking and answers with failure reasons
                thinking = getattr(result.output, 'thinking', 'No thinking provided')
                answers = getattr(result.output, 'answers', [])
                
                # Validate answers count
                if len(answers) != num_sql_candidates:
                    logger.warning(f"Evaluation {i}: Expected {num_sql_candidates} answers, got {len(answers)}")
                    # Pad or truncate as needed
                    if len(answers) < num_sql_candidates:
                        answers.extend(["Failed - incomplete evaluation"] * (num_sql_candidates - len(answers)))
                    else:
                        answers = answers[:num_sql_candidates]
                
                logger.info(f"Evaluation {i} completed with {len(answers)} verdicts")
                processed.append((thinking, answers))
                
            except Exception as e:
                logger.error(f"Error processing evaluation {i} result: {e}")
                error_answers = ["Failed - processing error"] * num_sql_candidates
                processed.append(("Error processing evaluation result", error_answers))
    
    return processed