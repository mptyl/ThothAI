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
from typing import List, Tuple, Any
from pydantic_ai.settings import ModelSettings
from model.evaluator_deps import EvaluatorDeps
from helpers.template_preparation import TemplateLoader
from agents.test_reducer_agent import create_test_reducer_agent, run_test_reducer

logger = logging.getLogger(__name__)

# Fixed temperature for all evaluators
EVALUATOR_TEMPERATURE = 0.2


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
    if len(unique_test_answers) > 5:  # Only use TestReducer if we have enough tests to benefit
        try:
            # Create TestReducer agent with evaluator's config
            evaluator_name = getattr(evaluator_agent, 'name', 'Unknown') if evaluator_agent else 'Unknown'
            test_reducer_agent = create_test_reducer_agent(
                model_config={'name': evaluator_name},
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
    
    # Format SQL candidates for template
    sql_candidates = []
    for i, sql in enumerate(state.generated_sqls, 1):
        sql_candidates.append(f"Candidate SQL #{i}:\n{sql}")
    candidate_sql_str = "\n\n".join(sql_candidates)
    
    # Format filtered tests as numbered list
    unit_tests_str = "\n".join([f"{i}. {test}" for i, test in enumerate(filtered_test_answers, 1)])
    
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
    
    # Prepare full context for the single evaluator
    context = {
        'question': state.question,
        'database_type': state.dbmanager.db_type if state.dbmanager else 'sqlite',
        'database_schema': state.used_mschema if hasattr(state, 'used_mschema') else state.full_mschema,
        'directives': state.directives if hasattr(state, 'directives') else '',
        'evidence': state.evidence_for_template if hasattr(state, 'evidence_for_template') else '',
        'candidate_sql': candidate_sql_str,
        'test_thinking': test_thinking,
        'unit_tests': unit_tests_str,
        'gold_sql_examples': gold_sql_examples_str
    }
    
    # Create single evaluation template with all unique tests
    # Map context keys to template placeholders
    template = TemplateLoader.format(
        'user_evaluate',
        safe=True,  # Use safe formatting for complex templates
        QUESTION=context['question'],
        TEST_THINKING=context['test_thinking'],
        DATABASE_TYPE=context['database_type'],
        DATABASE_SCHEMA=context['database_schema'],
        DIRECTIVES=context['directives'],
        EVIDENCE=context['evidence'],
        CANDIDATE_SQL=context['candidate_sql'],
        UNIT_TESTS=context['unit_tests'],
        GOLD_SQL_EXAMPLES=context['gold_sql_examples']
    )
    
    logger.info(f"Running SINGLE evaluator with {len(unique_test_answers)} unique tests against {len(state.generated_sqls)} SQL candidates")
    
    try:
        # Run single evaluator with FIXED temperature 0.2
        result = await evaluator_agent.run(
            template, 
            model_settings=ModelSettings(temperature=EVALUATOR_TEMPERATURE),
            deps=EvaluatorDeps()
        )
        
        if result and hasattr(result, 'output'):
            thinking = getattr(result.output, 'thinking', 'No thinking provided')
            answers = getattr(result.output, 'answers', [])
            
            # Log the actual answers received for debugging
            logger.info(f"Evaluator returned {len(answers)} answers")
            for i, ans in enumerate(answers, 1):
                logger.debug(f"Answer {i}: {ans[:100]}..." if len(ans) > 100 else f"Answer {i}: {ans}")
            
            # Validate answers count
            if len(answers) != len(state.generated_sqls):
                logger.warning(f"Expected {len(state.generated_sqls)} answers, got {len(answers)}")
                # Pad or truncate as needed
                if len(answers) < len(state.generated_sqls):
                    answers.extend([f"SQL #{i}: Failed - incomplete evaluation" for i in range(len(answers) + 1, len(state.generated_sqls) + 1)])
                else:
                    answers = answers[:len(state.generated_sqls)]
            
            logger.info(f"Single evaluation complete with {len(answers)} verdicts")
            # Return list of tuples as expected by evaluation_results: List[Tuple[str, List[str]]]
            # Store test answers separately if needed
            if hasattr(state, 'test_answers'):
                state.test_answers = filtered_test_answers  # Store filtered tests instead of unique
            # Store filtered tests for logging
            if hasattr(state, 'filtered_tests'):
                state.filtered_tests = filtered_test_answers
            return [(thinking, answers)]
        else:
            logger.error("Evaluator returned no output")
            return [("Evaluation failed - no output", ["Failed - no evaluation output"] * len(state.generated_sqls))]
            
    except Exception as e:
        logger.error(f"Evaluation failed with exception: {e}")
        return [(f"Evaluation error: {str(e)}", ["Failed - evaluation error"] * len(state.generated_sqls))]


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