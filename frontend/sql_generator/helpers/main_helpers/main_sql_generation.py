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
SQL generation orchestration for parallel SQL generation.
"""

import asyncio
import logging
from typing import List, Tuple
from pydantic_ai.settings import ModelSettings
from model.state_factory import StateFactory
from helpers.template_preparation import format_example_shots
from helpers.main_helpers.main_generate_mschema import generate_dynamic_mschema

logger = logging.getLogger(__name__)


def prepare_user_prompt_with_method(
    question: str,
    database_type: str,
    schema: str,
    directives: str,
    evidence: str,
    example_shots: str,
    method: str = "query_plan"
) -> str:
    """
    Prepare user prompt with specific methodology instructions.
    
    Args:
        question: The user's question
        database_type: Type of database (PostgreSQL, MySQL, etc.)
        schema: Database schema
        directives: Directives for SQL generation
        evidence: Evidence/hints
        example_shots: Example SQL queries
        method: Method to use ("query_plan", "step_by_step", "divide_and_conquer")
    
    Returns:
        Formatted user prompt with methodology instructions
    """
    import os
    from helpers.agents_utils import get_project_root
    
    # Map method to template file
    template_files = {
        "query_plan": "template_generate_sql_query_plan.txt",
        "step_by_step": "template_generate_sql_step_by_step.txt",
        "divide_and_conquer": "template_generate_sql_divide_and_conquer.txt"
    }
    
    template_file = template_files.get(method, "template_generate_sql_query_plan.txt")
    template_path = os.path.join(get_project_root(), "templates", template_file)
    
    # Load the template
    with open(template_path, "r") as file:
        raw_template = file.read()
    
    # Add database-specific NULL handling rules to directives
    db_type_lower = database_type.lower() if database_type else "sqlite"
    
    if db_type_lower == "sqlite":
        null_handling_rules = """
CRITICAL DATABASE RULE FOR SQLite:
- DO NOT use NULLS FIRST or NULLS LAST in ORDER BY clauses
- SQLite does not support this syntax and will throw an error
- Use plain ORDER BY without NULL position specifiers"""
    else:
        null_handling_rules = f"""
DATABASE RULE FOR {database_type}:
- Use NULLS LAST with ASC sorting
- Use NULLS FIRST with DESC sorting
- This database supports explicit NULL positioning in ORDER BY"""
    
    # Append null handling rules to directives
    enhanced_directives = (directives or "") + "\n\n" + null_handling_rules
    
    # Fill the template
    filled_template = raw_template.format(
        QUESTION=question,
        DATABASE_TYPE=database_type or "",
        DATABASE_SCHEMA=schema,
        DIRECTIVES=enhanced_directives,
        EVIDENCE=evidence or "",
        EXAMPLE_SHOTS=example_shots or ""
    )
    
    return filled_template


async def generate_sql_units(state, agents_and_tools, functionality_level) -> List[Tuple[bool, str]]:
    """
    Generate multiple SQL statements using the same agent with different user prompts and temperatures.
    Cycles through different methodologies (default, step_by_step, divide_and_conquer).
    
    Args:
        state: System state object containing configuration
        agents_and_tools: Agent manager with SQL agents
        functionality_level: Functionality level ("BASIC", "ADVANCED", "EXPERT")
    
    Returns:
        List of tuples containing (success, sql) for each generated SQL
    """
   
    # Calculate diverse temperature values for better SQL variation
    def calculate_diverse_temperatures(num_sqls):
        """Generate diverse temperatures for better SQL variation"""
        if num_sqls == 1:
            return [0.5]
        
        # Three groups of temperatures for maximum diversity
        low_temps = [0.1, 0.2, 0.3]   # Low creativity
        mid_temps = [0.5, 0.6, 0.7]   # Moderate creativity
        high_temps = [0.8, 0.9, 1.0]  # High creativity
        
        temperatures = []
        for i in range(num_sqls):
            # Distribute temperatures across groups in round-robin fashion
            # This ensures each method (query_plan, step_by_step, divide_and_conquer)
            # gets a mix of temperature ranges
            group_idx = i % 3
            within_group_idx = i // 3
            
            if group_idx == 0:
                temps = low_temps
            elif group_idx == 1:
                temps = mid_temps
            else:
                temps = high_temps
                
            temp_idx = within_group_idx % len(temps)
            temperatures.append(temps[temp_idx])
        
        return temperatures
    
    temperature_values = calculate_diverse_temperatures(state.number_of_sql_to_generate)
    logger.info(f"Using diverse temperatures for SQL generation: {temperature_values}")
  
    # Get the appropriate agent based on functionality level
    level = functionality_level.lower() if functionality_level else 'basic'
    if level == "basic":
        agent = agents_and_tools.sql_basic_agent
    elif level == "advanced":
        agent = agents_and_tools.sql_advanced_agent
    elif level == "expert":
        agent = agents_and_tools.sql_expert_agent
    else:
        agent = agents_and_tools.sql_basic_agent  # Default to basic
    
    if not agent:
        logger.error(f"No SQL agent found for functionality level: {functionality_level}")
        return [(False, "") for _ in range(state.number_of_sql_to_generate)]
    
    logger.info(f"Using {functionality_level} SQL agent for {state.number_of_sql_to_generate} generations")
    
    # Define the methods to cycle through
    methods = ["query_plan", "step_by_step", "divide_and_conquer"]
    
    # Create concurrent tasks for parallel SQL generation with round-robin methods
    tasks = []
    for i, temp in enumerate(temperature_values):
        # Round-robin selection of method
        method = methods[i % len(methods)]
        
        logger.info(f"SQL generation {i+1}: using {functionality_level} agent with {method} method, temp={temp}")
        
        # Create a task for each temperature value with selected method
        task = generate_single_sql_with_method(state, agent, temp, method, agent_index=i)
        tasks.append(task)
    
    # Execute all tasks in parallel and collect results
    sql_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results, handling any exceptions
    processed_results = []
    for i, result in enumerate(sql_results):
        if isinstance(result, Exception):
            logger.error(f"SQL generation {i+1} failed with exception: {result}")
            processed_results.append((False, ""))
        else:
            success, sql = result
            logger.info(f"SQL generation {i+1}: success={success}, sql_length={len(sql) if sql else 0}")
            processed_results.append(result)
    
    logger.info(f"Parallel SQL generation complete: {len(processed_results)} results")
    return processed_results


async def generate_single_sql_with_method(state, agent, temperature, method, agent_index=0):
    """
    Generate a single SQL statement with a specific temperature and method.
    
    Args:
        state: System state object
        agent: The SQL agent to use
        temperature: Temperature value for this generation
        method: Method to use ("query_plan", "step_by_step", "divide_and_conquer")
        agent_index: Index for logging purposes
    
    Returns:
        Tuple of (success, sql_string)
    """
    try:
        # Create lightweight dependencies using StateFactory
        sql_deps = StateFactory.create_agent_deps(state, "sql_generation")
        
        # Prepare the prompt data
        evidence_str = getattr(state, 'evidence_str', '')
        # Use sql_documents from state which contains actual SqlDocument objects
        sql_documents = getattr(state, 'sql_documents', [])
        # No fallback shots needed anymore - only use SQL documents from vector DB
        example_shots = format_example_shots(sql_documents)
        
        # Generate dynamic mschema WITH shuffle for variability
        dynamic_mschema = generate_dynamic_mschema(state, apply_shuffle=True)
        logger.debug(f"Generated dynamic mschema for SQL generation {agent_index + 1} with shuffle enabled")
        
        # Use the new method-specific user prompt
        user_prompt = prepare_user_prompt_with_method(
            question=state.question,
            database_type=state.dbmanager.db_type,
            schema=dynamic_mschema,
            directives=state.directives if hasattr(state, 'directives') else "",
            evidence=evidence_str,
            example_shots=example_shots,
            method=method
        )
        
        # Run the agent with lightweight deps and specified temperature
        await agent.run(
            user_prompt,
            deps=sql_deps,
            model_settings=ModelSettings(temperature=temperature)
        )
        
        # Check if generation was successful
        if sql_deps.last_generation_success and sql_deps.last_SQL:
            logger.info(f"SQL generation with {method} method successful (temp={temperature}): {sql_deps.last_SQL[:50]}...")
            return (True, sql_deps.last_SQL)
        else:
            logger.warning(f"SQL generation with {method} method failed (temp={temperature})")
            return (False, "")
            
    except Exception as e:
        logger.error(f"Individual SQL generation failed with {method} method: {e}")
        return (False, "")


def clean_sql_results(sql_list):
    """
    Clean SQL results by:
    1. Extracting SQL from tuples (success, sql)
    2. Removing entries containing 'GENERATION FAILED'
    3. Removing duplicate SQL statements
    
    Returns a list of unique, valid SQL strings
    """
    if not sql_list:
        return []
    
    cleaned_sqls = []
    seen_sqls = set()
    
    for item in sql_list:
        # Handle tuple format (success, sql) from generate_sql_units
        if isinstance(item, tuple):
            success, sql = item
            # Skip failed generations
            if not success:
                continue
        else:
            # Handle plain string format (backwards compatibility)
            sql = item
        
        # Skip if SQL is None or contains GENERATION FAILED
        if sql is None or not sql or "GENERATION FAILED" in sql:
            continue
            
        # Normalize SQL for comparison (strip whitespace)
        normalized_sql = sql.strip()
        
        # Skip empty strings
        if not normalized_sql:
            continue
            
        # Add only if not seen before (removes duplicates)
        if normalized_sql not in seen_sqls:
            seen_sqls.add(normalized_sql)
            cleaned_sqls.append(normalized_sql)
    
    return cleaned_sqls