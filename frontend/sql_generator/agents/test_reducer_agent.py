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
TestReducer agent for semantic test deduplication.

This agent eliminates semantically duplicate test cases to improve evaluation 
efficiency while maintaining comprehensive test coverage.
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic_ai import Agent

from agents.core.agent_result_models import TestReducerResult
from model.evaluator_deps import EvaluatorDeps
from helpers.template_preparation import TemplateLoader, clean_template_for_llm

logger = logging.getLogger(__name__)


def create_test_reducer_agent(
    model_config: Dict[str, Any],
    retries: int = 3
) -> Optional[Agent]:
    """
    Create a TestReducer agent for semantic test deduplication.
    
    This agent uses the same model configuration as the Evaluator to ensure
    consistency in reasoning and language understanding for test analysis.
    
    Args:
        model_config: Model configuration inherited from Evaluator
        retries: Number of retry attempts for agent execution
        
    Returns:
        Configured TestReducer Agent instance, or None if creation fails
    """
    from agents.core.agent_initializer import create_fallback_model
    
    # Create model using evaluator's configuration
    model = create_fallback_model(model_config, None)
    if not model:
        logger.error("Failed to create model for TestReducer agent")
        return None
    
    # Load system template
    try:
        system_prompt = TemplateLoader.load('sys_test_reducer')
    except Exception as e:
        logger.error(f"Failed to load TestReducer system template: {e}")
        return None
    
    # Create agent name
    agent_name = f"TestReducer - {model_config.get('name', 'Unknown')}"
    
    try:
        # Create the agent
        agent = Agent(
            model=model,
            name=agent_name,
            system_prompt=clean_template_for_llm(system_prompt),
            output_type=TestReducerResult,
            deps_type=EvaluatorDeps,  # Use same deps as Evaluator
            retries=retries
        )
        
        logger.info(f"Successfully created TestReducer agent: {agent_name}")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to create TestReducer agent: {e}")
        return None


async def run_test_reducer(
    test_reducer_agent: Agent,
    original_tests: List[str],
    test_thinking: str,
    question: str,
    database_schema: str
) -> Optional[TestReducerResult]:
    """
    Execute test reduction using the TestReducer agent.
    
    Args:
        test_reducer_agent: Configured TestReducer agent
        original_tests: List of original test cases
        test_thinking: Test generation reasoning from test generator
        question: Original user question
        database_schema: Database schema information
        
    Returns:
        TestReducerResult with reduced test list, or None on failure
    """
    try:
        # Format original tests for template
        original_tests_str = "\n".join([f"{i}. {test}" for i, test in enumerate(original_tests, 1)])
        
        # Create user template
        user_template = TemplateLoader.format(
            'user_test_reducer',
            safe=True,
            ORIGINAL_TESTS=original_tests_str,
            TEST_THINKING=test_thinking,
            QUESTION=question,
            DATABASE_SCHEMA=database_schema
        )
        
        # Run the agent
        result = await test_reducer_agent.run(
            user_template,
            deps=EvaluatorDeps()
        )
        
        if result and hasattr(result, 'output'):
            logger.info(f"TestReducer successfully reduced {len(original_tests)} tests to {len(result.output.reduced_tests)}")
            return result.output
        else:
            logger.error("TestReducer agent returned no output")
            return None
            
    except Exception as e:
        logger.error(f"Error running TestReducer agent: {e}")
        import traceback
        logger.error(f"TestReducer traceback: {traceback.format_exc()}")
        return None