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
Test generation orchestration for the CHRSS workflow.
"""

import asyncio
import logging
from helpers.template_preparation import TemplateLoader
from pydantic_ai.settings import ModelSettings
from helpers.main_helpers.main_generate_mschema import generate_dynamic_mschema

logger = logging.getLogger(__name__)


async def generate_test_units(state, agents_and_tools, functionality_level=None, timeout_seconds: int = 20):
    """
    Generate test units with variable temperature scaling from 0.5 to 1.0.
    Uses the fixed test_gen_agent_1 from workspace configuration.
    
    Args:
        state: System state object
        agents_and_tools: Agent manager with test agents
        functionality_level: Optional functionality level override (not used, kept for compatibility)
        timeout_seconds: Max seconds to wait for each individual test generation before timing out
    
    Returns:
        List of tuples (thinking, answers) for each test generation
    """ 
    # Get the fixed test_gen_agent_1 from agents_and_tools
    # The agent is already initialized from workspace configuration
    fixed_agent = getattr(agents_and_tools, 'test_gen_agent_1', None)
    
    if not fixed_agent:
        logger.error("No test_gen_agent_1 found in workspace configuration")
        return []
    
    # Format SQL candidates list for template
    sql_candidate_list = ""
    if hasattr(state, 'generated_sqls') and state.generated_sqls:
        sql_candidates = []
        for i, sql in enumerate(state.generated_sqls, 1):
            sql_candidates.append(f"Candidate SQL #{i}:\n{sql}")
        sql_candidate_list = "\n\n".join(sql_candidates)
    else:
        logger.warning("No SQL candidates found in state.generated_sqls")
        sql_candidate_list = "No SQL candidates available"
    
    # Use the same fixed agent for all test generations
    agents_to_use = [fixed_agent] * state.number_of_tests_to_generate
    logger.info(f"Using fixed test_gen_agent_1 from workspace for all {state.number_of_tests_to_generate} test generations")
    
    # Calculate temperature values from 0.5 to 1.0
    # Linear scaling: start at 0.5 and increase to 1.0
    min_temp = 0.5
    max_temp = 1.0
    
    # Create temperature values with max 2 decimal places
    temperature_values = []
    for i in range(state.number_of_tests_to_generate):
        if state.number_of_tests_to_generate == 1:
            temp = min_temp
        else:
            temp = min_temp + (max_temp - min_temp) * (i / (state.number_of_tests_to_generate - 1))
        # Round to 2 decimal places
        temp = round(temp, 2)
        temperature_values.append(temp)
    
    # Create concurrent tasks for parallel execution
    tasks = []
    for i, temp in enumerate(temperature_values):
        # Generate dynamic mschema WITHOUT shuffle (as per requirements)
        dynamic_mschema = generate_dynamic_mschema(state, apply_shuffle=False)
        logger.debug(f"Generated dynamic mschema for test {i+1} without shuffle")
        
        # Prepare template parameters with dynamic mschema and SQL candidates
        template_params = {
            'directives': getattr(state, 'directives', '') or "",
            'dbmanager': state.dbmanager,
            'used_mschema': dynamic_mschema,  # Use dynamic mschema instead of state.used_mschema
            'question': state.question,
            'evidence_for_template': getattr(state, 'evidence_for_template', '') or "",
            'sql_candidate_list': sql_candidate_list  # Pass SQL candidates for evaluation
        }
        
        # Create test generator template with unique mschema and SQL candidates
        template = TemplateLoader.format(
            'template_generate_unit_tests.txt',
            safe=True,  # Use safe formatting for complex templates
            **template_params
        )
        
        # Use the fixed agent from the agents_to_use list
        agent = agents_to_use[i]
        logger.info(f"Test generation {i+1}: Using fixed test_gen_agent_1 with temperature {temp}")
        # Protect each individual test generation with a timeout to avoid hangs
        task = asyncio.wait_for(
            agent.run(template, model_settings=ModelSettings(temperature=temp)),
            timeout=timeout_seconds
        )
        tasks.append(task)
    
    # Execute all tasks in parallel and collect results, handling exceptions
    test_result_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results, handling any exceptions and creating simple test results
    processed_results = []
    for i, result in enumerate(test_result_list):
        if isinstance(result, Exception):
            logger.error(f"Test generation {i+1} failed with exception: {result}")
            # Create a simple failure result (thinking, answers)
            processed_results.append(("GENERATION FAILED", ["GENERATION FAILED"]))
        else:
            # Valid result - extract thinking and answers
            if hasattr(result, 'output'):
                thinking = getattr(result.output, 'thinking', '')
                answers = getattr(result.output, 'answers', [])
                logger.info(f"Test {i+1} generated with {len(answers)} test units")
                processed_results.append((thinking, answers))
            else:
                logger.warning(f"Test {i+1} result has no output attribute")
                processed_results.append(("Invalid result", []))
    
    logger.info(f"Parallel test generation complete: {len(processed_results)} tests processed")
    return processed_results