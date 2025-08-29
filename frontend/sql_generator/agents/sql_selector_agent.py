# Copyright (c) 2025 Marco Pancotti
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
SqlSelector agent for choosing the best SQL from equivalent candidates.

This agent handles Case B in the 4-case evaluation system: when multiple 
SQL candidates have achieved 100% test pass rates, it selects the best one
based on quality criteria including simplicity, performance, and maintainability.
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic_ai import Agent

from agents.core.agent_result_models import SqlSelectorResult
from model.evaluator_deps import EvaluatorDeps
from helpers.template_preparation import TemplateLoader, clean_template_for_llm

logger = logging.getLogger(__name__)


def create_sql_selector_agent(
    model_config: Dict[str, Any],
    retries: int = 3
) -> Optional[Agent]:
    """
    Create a SqlSelector agent for choosing the best SQL from equivalent candidates.
    
    This agent uses the same model configuration as the Evaluator to ensure
    consistency in reasoning and SQL quality assessment.
    
    Args:
        model_config: Model configuration inherited from Evaluator
        retries: Number of retry attempts for agent execution
        
    Returns:
        Configured SqlSelector Agent instance, or None if creation fails
    """
    from agents.core.agent_initializer import create_fallback_model
    
    # Create model using evaluator's configuration
    model = create_fallback_model(model_config, None)
    if not model:
        logger.error("Failed to create model for SqlSelector agent")
        return None
    
    # Load system template
    try:
        system_prompt = TemplateLoader.load('sys_sql_selector')
    except Exception as e:
        logger.error(f"Failed to load SqlSelector system template: {e}")
        return None
    
    # Create agent name
    agent_name = f"SqlSelector - {model_config.get('name', 'Unknown')}"
    
    try:
        # Create the agent
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=SqlSelectorResult,
            deps_type=EvaluatorDeps,  # Use same deps as Evaluator
            retries=retries
        )
        
        logger.info(f"Successfully created SqlSelector agent: {agent_name}")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to create SqlSelector agent: {e}")
        return None


async def run_sql_selector(
    sql_selector_agent: Agent,
    question: str,
    database_schema: str,
    equivalent_sqls: List[str],
    test_results_context: str,
    gold_sql_examples: List[str] = None
) -> Optional[SqlSelectorResult]:
    """
    Execute SQL selection using the SqlSelector agent.
    
    Args:
        sql_selector_agent: Configured SqlSelector agent
        question: Original user question
        database_schema: Database schema information
        equivalent_sqls: List of SQL queries that passed 100% of tests
        test_results_context: Context about how the tests were passed
        gold_sql_examples: Optional Gold SQL examples for reference
        
    Returns:
        SqlSelectorResult with selected SQL index and reasoning, or None on failure
    """
    try:
        # Format equivalent SQLs for template
        formatted_sqls = []
        for i, sql in enumerate(equivalent_sqls):
            formatted_sqls.append(f"Candidate #{i} (Index {i}):\n{sql}")
        equivalent_sqls_str = "\n\n".join(formatted_sqls)
        
        # Format Gold SQL examples if available
        gold_sql_examples_str = ""
        if gold_sql_examples:
            formatted_gold_examples = []
            for i, gold_sql in enumerate(gold_sql_examples, 1):
                formatted_gold_examples.append(f"Example #{i}:\n{gold_sql}")
            gold_sql_examples_str = "\n\n".join(formatted_gold_examples)
        else:
            gold_sql_examples_str = "No Gold SQL examples available for reference."
        
        # Create user template
        user_template = TemplateLoader.format(
            'user_sql_selector',
            safe=True,
            QUESTION=question,
            DATABASE_SCHEMA=database_schema,
            EQUIVALENT_SQLS=equivalent_sqls_str,
            TEST_RESULTS_CONTEXT=test_results_context,
            GOLD_SQL_EXAMPLES=gold_sql_examples_str
        )
        
        # Run the agent
        result = await sql_selector_agent.run(
            user_template,
            deps=EvaluatorDeps()
        )
        
        if result and hasattr(result, 'output'):
            logger.info(f"SqlSelector selected SQL index {result.output.selected_index} from {len(equivalent_sqls)} candidates")
            return result.output
        else:
            logger.error("SqlSelector agent returned no output")
            return None
            
    except Exception as e:
        logger.error(f"Error running SqlSelector agent: {e}")
        import traceback
        logger.error(f"SqlSelector traceback: {traceback.format_exc()}")
        return None