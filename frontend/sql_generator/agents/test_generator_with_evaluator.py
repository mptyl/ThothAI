#!/usr/bin/env python

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
Test generator agent with integrated evaluator tool.
This agent creates test units and evaluates SQL candidates in one go.
"""

import logging
from typing import List, Tuple, Dict, Any
from pydantic_ai import Agent, RunContext
from agents.core.agent_result_models import TestUnitGeneratorResult
from model.evaluator_deps import EvaluatorDeps
from helpers.template_preparation import TemplateLoader

logger = logging.getLogger(__name__)


def create_test_generator_with_evaluator(
    model_config: Dict[str, Any],
    evaluator_agent: Agent,
    system_prompt: str,
    retries: int = 3
) -> Agent:
    """
    Create a test generator agent with an integrated evaluator tool.
    
    Args:
        model_config: Model configuration for the test generator
        evaluator_agent: The evaluator agent to use for evaluation
        system_prompt: System prompt for the test generator
        retries: Number of retries for the agent
        
    Returns:
        Agent configured with evaluator tool
    """
    from agents.core.agent_initializer import create_fallback_model
    
    # Create the model
    model = create_fallback_model(model_config, None)
    if not model:
        return None
    
    # Create the agent
    agent = Agent(
        model=model,
        name=f"Test Generator with Evaluator - {model_config.get('name', 'Unknown')}",
        system_prompt=system_prompt,
        output_type=TestUnitGeneratorResult,
        retries=retries
    )
    
    # Add the evaluator tool
    @agent.tool
    async def evaluator_tool(
        ctx: RunContext,
        question: str,
        test_thinking: str,
        database_type: str,
        database_schema: str,
        directives: str,
        evidence: str,
        unit_tests: List[str],
        candidate_sqls: List[str]
    ) -> Tuple[str, List[str]]:
        """Evaluate SQL candidates against unit tests and return thinking and verdicts."""
        logger.debug(f"EVALUATOR TOOL CALLED with {len(unit_tests)} tests and {len(candidate_sqls)} SQL candidates")
        
        try:
            # Format unit tests
            unit_tests_str = "\n".join([f"{i}. {test}" for i, test in enumerate(unit_tests, 1)])
            
            # Format candidate SQLs
            candidate_sql_str = "\n\n".join([f"Candidate SQL #{i}:\n{sql}" for i, sql in enumerate(candidate_sqls, 1)])
            
            # Create evaluator template with test thinking
            eval_template = TemplateLoader.format(
                'user_evaluate',
                safe=True,
                QUESTION=question,
                TEST_THINKING=test_thinking,
                DATABASE_TYPE=database_type,
                DATABASE_SCHEMA=database_schema,
                DIRECTIVES=directives,
                EVIDENCE=evidence,
                CANDIDATE_SQL=candidate_sql_str,
                UNIT_TESTS=unit_tests_str
            )
            
            # Run evaluator agent
            evaluator_deps = EvaluatorDeps()
            eval_result = await evaluator_agent.run(
                eval_template,
                deps=evaluator_deps
            )
            
            if eval_result and hasattr(eval_result, 'output'):
                logger.debug(f"EVALUATOR TOOL SUCCESS - Thinking: {eval_result.output.thinking[:100]}...")
                logger.debug(f"EVALUATOR TOOL SUCCESS - Answers: {eval_result.output.answers}")
                return (eval_result.output.thinking, eval_result.output.answers)
            else:
                logger.warning("EVALUATOR TOOL FAILED - No output from evaluator agent")
                return ("Evaluation failed", ["Failed"] * len(candidate_sqls))
                
        except Exception as e:
            logger.error(f"EVALUATOR TOOL EXCEPTION: {e}")
            import traceback
            logger.error(f"EVALUATOR TOOL TRACEBACK: {traceback.format_exc()}")
            return (f"Evaluation error: {str(e)}", ["Failed"] * len(candidate_sqls))
    
    return agent