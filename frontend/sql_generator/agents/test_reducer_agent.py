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
import re
from typing import Dict, Any, Optional, List
from pydantic_ai import Agent

from agents.core.agent_result_models import TestReducerResult
from model.evaluator_deps import EvaluatorDeps
from helpers.template_preparation import TemplateLoader, clean_template_for_llm

logger = logging.getLogger(__name__)


_EVIDENCE_TAG_PATTERN = re.compile(r"\[\s*EVIDENCE-CRITICAL\s*\]", re.IGNORECASE)


def _normalize_test_text(text: str) -> str:
    """Normalize a test string for matching while ignoring evidence tags and minor punctuation."""
    if not isinstance(text, str):
        return ""
    without_tag = _EVIDENCE_TAG_PATTERN.sub("", text)
    without_numbering = re.sub(r"^\s*\d+[\.)-]\s*", "", without_tag)
    collapsed = re.sub(r"\s+", " ", without_numbering)
    return collapsed.strip().lower()


def _preserve_evidence_tags(original_tests: List[str], reduced_tests: List[str]) -> List[str]:
    """Ensure tests marked evidence-critical retain their tag after reduction."""
    critical_signatures = {
        _normalize_test_text(test)
        for test in original_tests
        if isinstance(test, str) and _EVIDENCE_TAG_PATTERN.search(test)
    }

    if not critical_signatures:
        return reduced_tests

    preserved: List[str] = []
    for test in reduced_tests:
        if not isinstance(test, str):
            preserved.append(test)
            continue

        normalized = _normalize_test_text(test)
        has_tag = bool(_EVIDENCE_TAG_PATTERN.search(test))

        if normalized in critical_signatures and not has_tag:
            # Reapply tag without disturbing existing formatting unnecessarily
            trimmed = test.lstrip()
            prefixed = f"[EVIDENCE-CRITICAL] {trimmed}" if trimmed else "[EVIDENCE-CRITICAL]"
            preserved.append(prefixed)
        else:
            preserved.append(test)

    return preserved


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
        system_prompt = TemplateLoader.load('system_templates/system_template_test_reducer')
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
    test_thinking: str = None,
    question: str = None,
    database_schema: str = None
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
        
        # Create user template - simplified, only tests
        user_template = TemplateLoader.format(
            'template_test_reducer.txt',
            safe=True,
            ORIGINAL_TESTS=original_tests_str
        )
        
        # Run the agent
        result = await test_reducer_agent.run(
            user_template,
            deps=EvaluatorDeps()
        )

        if result and hasattr(result, 'output'):
            logger.info(
                f"TestReducer successfully reduced {len(original_tests)} tests to {len(result.output.reduced_tests)}"
            )

            try:
                preserved = _preserve_evidence_tags(original_tests, result.output.reduced_tests)
                result.output.reduced_tests = preserved
            except Exception as e:  # pragma: no cover - defensive guard
                logger.error(f"Failed to preserve evidence-critical tags: {e}")

            return result.output
        else:
            logger.error("TestReducer agent returned no output")
            return None
            
    except Exception as e:
        logger.error(f"Error running TestReducer agent: {e}")
        import traceback
        logger.error(f"TestReducer traceback: {traceback.format_exc()}")
        return None
