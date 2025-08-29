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
Test validators for test generation and execution agents.
"""

from typing import List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TestValidators:
    """
    Validators for test generation and execution agents.
    """
    
    def __init__(self):
        """Initialize test validators."""
        pass
    
    def create_test_gen_validator(self):
        """
        Create a test generation validator.
        
        Returns:
            A validator function for test generation
        """
        def validator(value):
            """Validate test generation output."""
            return self.validate_test_generation_output(value)
        return validator
    
    def create_test_exec_validator(self):
        """
        Create a test execution validator.
        
        Returns:
            A validator function for test execution
        """
        def validator(value):
            """Validate test execution output."""
            # Basic validation - can be extended
            return value is not None
        return validator
    
    def validate_test_results(self, test_results: List[Any]) -> bool:
        """
        Validate test results from test generation agents.
        
        Args:
            test_results: List of test results from agents
            
        Returns:
            True if all tests are valid, False otherwise
        """
        if not test_results:
            logger.warning("No test results to validate")
            return False
            
        for result in test_results:
            if not self._validate_single_test(result):
                return False
                
        return True
    
    def _validate_single_test(self, test_result: Any) -> bool:
        """
        Validate a single test result.
        
        Args:
            test_result: Single test result to validate
            
        Returns:
            True if test is valid, False otherwise
        """
        # Basic validation - can be extended as needed
        if test_result is None:
            logger.error("Test result is None")
            return False
            
        # Check if result has expected structure
        if not hasattr(test_result, 'output'):
            logger.error("Test result missing output attribute")
            return False
            
        return True
    
    def validate_test_generation_output(self, output: Any) -> bool:
        """
        Validate output from test generation agent.
        
        Args:
            output: Output from test generation agent
            
        Returns:
            True if output is valid, False otherwise
        """
        if output is None:
            logger.error("Test generation output is None")
            return False
            
        # Check for required fields in TestUnitGeneratorResult
        required_fields = ['thinking', 'answers', 'evaluator_thinking', 'evaluator_answers']
        
        for field in required_fields:
            if not hasattr(output, field):
                logger.error(f"Test generation output missing field: {field}")
                return False
                
        return True
    
    def create_evaluator_validator(self):
        """
        Create an evaluator validator that ensures both thinking and answers are present.
        
        Returns:
            Async validator function that raises ModelRetry if validation fails
        """
        async def validate_evaluation_output(ctx, result):
            """
            Validate evaluator output has both thinking and answers.
            Raises ModelRetry if validation fails.
            
            Args:
                ctx: RunContext with EvaluatorDeps
                result: EvaluationResult from the evaluator agent
            """
            from pydantic_ai import ModelRetry
            
            # Check thinking is present and not empty
            if not result.thinking or result.thinking.strip() in ["", "..."]:
                raise ModelRetry(
                    "Please provide detailed thinking about your evaluation process. "
                    "Explain how you evaluated each candidate SQL against the test criteria."
                )
            
            # Check answers list exists and is not empty
            if not result.answers or len(result.answers) == 0:
                raise ModelRetry(
                    "Please provide evaluation answers for all candidate SQL queries. "
                    "Each answer should be 'Passed' or 'Failed - <short reason>'."
                )
            
            # Log successful validation
            logger.info(f"Evaluator validation passed: {len(result.answers)} answers provided")
            
            # Validation passed
            return result
        
        return validate_evaluation_output