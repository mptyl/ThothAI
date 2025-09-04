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

# Unless required by applicable law or agreed to in writing, software
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""
EvaluatorSupervisor agent for deep reevaluation of borderline SQL candidates.

This agent handles Case C in the 4-case evaluation system: when SQL candidates 
score 90-99%, it performs extended analysis (8000+ token thinking) to make final 
GOLD/FAILED decisions with high confidence.
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from agents.core.agent_result_models import EvaluatorSupervisorResult
from model.evaluator_deps import EvaluatorDeps
from helpers.template_preparation import TemplateLoader, clean_template_for_llm

logger = logging.getLogger(__name__)

# Extended thinking temperature for deep analysis
SUPERVISOR_TEMPERATURE = 0.1  # Lower temperature for more focused analysis


def create_evaluator_supervisor_agent(
    model_config: Dict[str, Any],
    retries: int = 3
) -> Optional[Agent]:
    """
    Create an EvaluatorSupervisor agent for deep reevaluation of borderline cases.
    
    This agent uses the same model configuration as the Evaluator but with lower
    temperature for more focused analysis and extended thinking capacity.
    
    Args:
        model_config: Model configuration inherited from Evaluator
        retries: Number of retry attempts for agent execution
        
    Returns:
        Configured EvaluatorSupervisor Agent instance, or None if creation fails
    """
    from agents.core.agent_initializer import create_fallback_model
    
    # Create model using evaluator's configuration
    model = create_fallback_model(model_config, None)
    if not model:
        logger.error("Failed to create model for EvaluatorSupervisor agent")
        return None
    
    # Load system template
    try:
        system_prompt = TemplateLoader.load('sys_evaluator_supervisor')
    except Exception as e:
        logger.error(f"Failed to load EvaluatorSupervisor system template: {e}")
        return None
    
    # Create agent name
    agent_name = f"EvaluatorSupervisor - {model_config.get('name', 'Unknown')}"
    
    try:
        # Create the agent
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=EvaluatorSupervisorResult,
            deps_type=EvaluatorDeps,  # Use same deps as Evaluator
            retries=retries
        )
        
        logger.info(f"Successfully created EvaluatorSupervisor agent: {agent_name}")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to create EvaluatorSupervisor agent: {e}")
        return None


async def run_evaluator_supervisor(
    supervisor_agent: Agent,
    question: str,
    database_schema: str,
    borderline_sqls: List[str],
    initial_evaluation: str,
    test_details: str,
    initial_thinking: str,
    gold_sql_examples: List[str] = None,
    evaluation_threshold: int = 90
) -> Optional[EvaluatorSupervisorResult]:
    """
    Execute deep reevaluation using the EvaluatorSupervisor agent.
    
    Args:
        supervisor_agent: Configured EvaluatorSupervisor agent
        question: Original user question
        database_schema: Database schema information
        borderline_sqls: List of SQL queries that scored 90-99%
        initial_evaluation: Initial evaluation results
        test_details: Detailed information about the tests
        initial_thinking: Original evaluator's reasoning
        gold_sql_examples: Optional Gold SQL examples for reference
        
    Returns:
        EvaluatorSupervisorResult with final decision and reasoning, or None on failure
    """
    try:
        # Format borderline SQLs for template
        formatted_sqls = []
        for i, sql in enumerate(borderline_sqls):
            formatted_sqls.append(f"Borderline SQL #{i} (Index {i}):\n{sql}")
        borderline_sqls_str = "\n\n".join(formatted_sqls)
        
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
            'template_evaluator_supervisor.txt',
            safe=True,
            QUESTION=question,
            DATABASE_SCHEMA=database_schema,
            BORDERLINE_SQLS=borderline_sqls_str,
            INITIAL_EVALUATION=initial_evaluation,
            TEST_DETAILS=test_details,
            INITIAL_THINKING=initial_thinking,
            GOLD_SQL_EXAMPLES=gold_sql_examples_str,
            EVALUATION_THRESHOLD=evaluation_threshold
        )
        
        # Run the agent with lower temperature for focused analysis
        result = await supervisor_agent.run(
            user_template,
            model_settings=ModelSettings(temperature=SUPERVISOR_TEMPERATURE),
            deps=EvaluatorDeps()
        )
        
        if result and hasattr(result, 'output'):
            logger.info(f"EvaluatorSupervisor made {result.output.final_decision.value} decision with {result.output.confidence_level} confidence")
            return result.output
        else:
            logger.error("EvaluatorSupervisor agent returned no output")
            return None
            
    except Exception as e:
        logger.error(f"Error running EvaluatorSupervisor agent: {e}")
        import traceback
        logger.error(f"EvaluatorSupervisor traceback: {traceback.format_exc()}")
        return None